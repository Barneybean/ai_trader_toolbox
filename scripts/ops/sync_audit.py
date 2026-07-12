#!/usr/bin/env python3
"""Read-only source-to-open-source sync auditor.

This tool inventories a source checkout and the public target, classifies every
difference through docs/source-sync-policy.json, and checks the target's safety
invariants. It NEVER copies, edits, stages, commits, or pushes files.

Examples:
  python3 scripts/ops/sync_audit.py --source ../trading-desk
  python3 scripts/ops/sync_audit.py --source /path/to/user-worktree --json
  python3 scripts/ops/sync_audit.py --self-test

For a branch in the same repository, create a separate worktree and pass it as
--source. Shared repositories are blocked unless --allow-shared-repository is
explicitly supplied because branch separation is not a privacy firewall.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_POLICY = ROOT / "docs" / "source-sync-policy.json"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}
MAX_HASH_BYTES = 20 * 1024 * 1024


def load_policy(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported sync policy schema: {data.get('schema_version')!r}")
    if not isinstance(data.get("policy_id"), str) or not data["policy_id"]:
        raise ValueError("sync policy requires a non-empty policy_id")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(data.get("policy_version", ""))):
        raise ValueError("sync policy requires a semantic policy_version (X.Y.Z)")
    classes = data.get("classes")
    if not isinstance(classes, list) or not classes:
        raise ValueError("sync policy requires ordered classes")
    names: set[str] = set()
    for rule in classes:
        if not isinstance(rule, dict) or not isinstance(rule.get("name"), str):
            raise ValueError("each sync class requires a string name")
        if rule["name"] in names:
            raise ValueError(f"duplicate sync class: {rule['name']}")
        names.add(rule["name"])
        if not isinstance(rule.get("action"), str):
            raise ValueError(f"sync class {rule['name']} requires an action")
        if not all(isinstance(p, str) and p for p in rule.get("patterns", [])):
            raise ValueError(f"sync class {rule['name']} has an invalid pattern")
        for pattern in rule.get("patterns", []):
            glob_regex(pattern)
    if not isinstance(data.get("default_class"), str) or not data["default_class"]:
        raise ValueError("sync policy requires a non-empty default_class")
    canonical = data.get("canonical_paths", [])
    if not isinstance(canonical, list):
        raise ValueError("canonical_paths must be a list")
    canonical_ids: set[str] = set()
    canonical_paths: set[str] = set()
    for item in canonical:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or not isinstance(item.get("path"), str) or not item["id"] or not item["path"]):
            raise ValueError("canonical_paths entries require id and path")
        if item["id"] in canonical_ids or item["path"] in canonical_paths:
            raise ValueError(f"duplicate canonical path entry: {item}")
        if not isinstance(item.get("aliases", []), list):
            raise ValueError(f"canonical path aliases must be a list: {item['id']}")
        canonical_ids.add(item["id"])
        canonical_paths.add(item["path"])
    aliases: set[str] = set()
    for item in canonical:
        for alias in item.get("aliases", []):
            if not isinstance(alias, str) or not alias or alias in aliases or alias in canonical_paths:
                raise ValueError(f"duplicate/conflicting canonical alias: {alias}")
            aliases.add(alias)
    if not all(isinstance(p, str) and p for p in data.get("required_paths", [])):
        raise ValueError("required_paths must contain non-empty strings")
    required_text = data.get("required_text", {})
    if not isinstance(required_text, dict) or not all(
        isinstance(path, str) and path and isinstance(values, list)
        and all(isinstance(value, str) and value for value in values)
        for path, values in required_text.items()
    ):
        raise ValueError("required_text must map paths to non-empty string lists")
    for entry in data.get("sensitive_regexes", []):
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("pattern"):
            raise ValueError("sensitive_regexes entries require name and pattern")
        re.compile(entry["pattern"])
    return data


def glob_regex(pattern: str) -> re.Pattern[str]:
    """Compile a slash-aware glob: * stays within a path part; ** crosses parts."""
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def compiled_classes(policy: dict[str, Any]) -> list[tuple[str, str, list[re.Pattern[str]]]]:
    return [
        (rule["name"], rule["action"], [glob_regex(p) for p in rule.get("patterns", [])])
        for rule in policy["classes"]
    ]


def classify(rel: str, rules: list[tuple[str, str, list[re.Pattern[str]]]],
             default: str) -> tuple[str, str]:
    rel = rel.replace(os.sep, "/")
    if rel.startswith("./"):
        rel = rel[2:]
    rel = rel.lstrip("/")
    for name, action, patterns in rules:
        if any(p.match(rel) for p in patterns):
            return name, action
    return default, "Human classification required before any port."


def inventory(root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        base = Path(dirpath)
        for name in sorted(filenames):
            p = base / name
            rel = p.relative_to(root).as_posix()
            out[rel] = p
    return out


def publishable_files(root: Path) -> set[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True,
        )
        return {line for line in proc.stdout.splitlines() if line}
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set(inventory(root))


def digest(path: Path) -> str:
    if path.is_symlink():
        return "symlink:" + os.readlink(path)
    try:
        if path.stat().st_size > MAX_HASH_BYTES:
            st = path.stat()
            return f"large:{st.st_size}:{st.st_mtime_ns}"
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except OSError as exc:
        return f"unreadable:{type(exc).__name__}"


def git_output(root: Path, *args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def git_common_dir(root: Path) -> Path | None:
    value = git_output(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(value).resolve() if value else None


def normalize_remote(url: str) -> str:
    value = url.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.casefold()


def git_remotes(root: Path) -> set[str]:
    out = git_output(root, "remote", "-v")
    if not out:
        return set()
    urls = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            urls.add(normalize_remote(parts[1]))
    return urls


def line_matches(path: Path, regex: re.Pattern[str]) -> list[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        if regex.search(line):
            hits.append((number, line.strip()[:180]))
    return hits


def load_deny_terms(target: Path, policy: dict[str, Any],
                    extra_paths: list[Path]) -> list[str]:
    paths = [target / rel for rel in policy.get("local_denylist_paths", [])] + extra_paths
    terms: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            value = raw.strip()
            if value and not value.startswith("#"):
                terms.append(value)
    return sorted(set(terms), key=str.casefold)


def check_env_example(target: Path, policy: dict[str, Any], errors: list[str]) -> None:
    path = target / "chat-bot-bridge" / ".env.example"
    if not path.is_file():
        return
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    for key in policy.get("secret_env_keys", []):
        if values.get(key):
            errors.append(f"chat-bot-bridge/.env.example: secret/id placeholder {key} must be blank")


def target_safety(target: Path, target_files: dict[str, Path], policy: dict[str, Any],
                  rules: list[tuple[str, str, list[re.Pattern[str]]]],
                  deny_terms: list[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    publishable = publishable_files(target)

    for rel in policy.get("required_paths", []):
        if not (target / rel).exists():
            errors.append(f"missing required public path: {rel}")
    for item in policy.get("canonical_paths", []):
        canonical = item["path"]
        if item.get("required") and not (target / canonical).exists():
            errors.append(f"missing canonical public path: {canonical}")
        for alias in item.get("aliases", []):
            if (target / alias).exists():
                errors.append(f"obsolete alias {alias}; use canonical path {canonical}")

    for rel in sorted(publishable):
        category, _ = classify(rel, rules, policy["default_class"])
        if category == "never_import" and (target / rel).exists():
            errors.append(f"publishable target contains private/runtime path: {rel}")

    for rel, required in policy.get("required_text", {}).items():
        path = target / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for literal in required:
            if literal not in text:
                errors.append(f"{rel}: missing safety invariant text {literal!r}")

    sensitive = [
        (entry["name"], re.compile(entry["pattern"]))
        for entry in policy.get("sensitive_regexes", [])
    ]
    scan_exclude = set(policy.get("sensitive_scan_exclude", []))
    for rel in sorted(publishable):
        if rel in scan_exclude:
            continue
        path = target / rel
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        for name, regex in sensitive:
            for line_no, _ in line_matches(path, regex):
                errors.append(f"{rel}:{line_no}: {name}")
        if deny_terms:
            text = path.read_text(encoding="utf-8", errors="replace").casefold()
            for term in deny_terms:
                if term.casefold() in text:
                    errors.append(f"{rel}: local denylist term present ({term[:3]}…)")
    check_env_example(target, policy, errors)
    return sorted(set(errors)), warnings


def compare(source: Path, target: Path, policy: dict[str, Any],
            allow_shared: bool, deny_paths: list[Path]) -> dict[str, Any]:
    rules = compiled_classes(policy)
    source_files = inventory(source)
    target_files = inventory(target)
    target_publishable = publishable_files(target)
    errors: list[str] = []
    warnings: list[str] = []

    source_git = git_common_dir(source)
    target_git = git_common_dir(target)
    if source_git and target_git and source_git == target_git:
        message = "source and public target share one git repository; branch separation is not a privacy firewall"
        (warnings if allow_shared else errors).append(message)

    source_remotes, target_remotes = git_remotes(source), git_remotes(target)
    if source_remotes and target_remotes and source_remotes.intersection(target_remotes):
        errors.append("source and public target share a git remote; remove the cross-repo push path")

    deny_terms = load_deny_terms(target, policy, deny_paths)
    safety_errors, safety_warnings = target_safety(
        target, target_files, policy, rules, deny_terms
    )
    errors.extend(safety_errors)
    warnings.extend(safety_warnings)

    rows = []
    counts: Counter[str] = Counter()
    for rel in sorted(set(source_files) | set(target_files)):
        in_source = rel in source_files
        in_target = rel in target_files
        category, action = classify(rel, rules, policy["default_class"])
        if in_source and in_target:
            same = digest(source_files[rel]) == digest(target_files[rel])
            state = "same" if same else "changed"
        elif in_source:
            state = "source_only"
        else:
            state = "target_only"

        if state == "same":
            disposition = "no_action"
        elif category == "never_import":
            disposition = "blocked_by_design"
        elif category == "preserve_public":
            disposition = "preserve_public"
        elif category == "sanitize_required":
            disposition = "manual_sanitization"
        elif category == "reusable_candidate":
            disposition = "review_candidate"
        else:
            disposition = "manual_classification"

        counts[disposition] += 1
        if state != "same":
            rows.append({
                "path": rel,
                "state": state,
                "class": category,
                "disposition": disposition,
                "action": action,
                "target_publishable": rel in target_publishable,
            })

    return {
        "report_schema_version": 1,
        "policy": {
            "id": policy["policy_id"],
            "version": policy["policy_version"],
            "schema_version": policy["schema_version"],
        },
        "source": str(source),
        "target": str(target),
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "summary": dict(sorted(counts.items())),
        "differences": rows,
        "safe_to_begin_manual_port": not errors,
        "automatic_copy_permitted": False,
    }


def print_text(report: dict[str, Any], limit: int) -> None:
    print("Source sync audit (read-only)")
    print(f"  source: {report['source']}")
    print(f"  target: {report['target']}")
    print("  automatic copy: NEVER")
    print("Summary:")
    for key, value in report["summary"].items():
        print(f"  {key}: {value}")
    for warning in report["warnings"]:
        print(f"  WARN {warning}")
    for error in report["errors"]:
        print(f"  ERR  {error}")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in report["differences"]:
        grouped[row["disposition"]].append(row)
    shown = 0
    for disposition in (
        "review_candidate", "manual_sanitization", "manual_classification",
        "preserve_public", "blocked_by_design",
    ):
        rows = grouped.get(disposition, [])
        if not rows:
            continue
        print(f"\n{disposition} ({len(rows)}):")
        for row in rows:
            if shown >= limit:
                print(f"  … output limited to {limit}; use --json for the full inventory")
                break
            print(f"  {row['state']:<11} {row['path']}")
            shown += 1
        if shown >= limit:
            break

    print("\nRequired workflow:")
    print("  1. Fix every ERR before porting.")
    print("  2. Preserve public-only files and compatibility paths.")
    print("  3. Port review candidates manually; sanitize required files instead of copying.")
    print("  4. Run consistency, PII, syntax/behavior tests, and the significant-change smoke gate.")
    print("  5. Human-review the public diff, then commit/push only from the public repository.")


def self_test(policy: dict[str, Any]) -> int:
    rules = compiled_classes(policy)
    cases = {
        ".claude/settings.json": "never_import",
        ".env.example": "never_import",
        "logs/desk.log": "never_import",
        "chat-bot-bridge/.env": "never_import",
        "SECURITY.md": "preserve_public",
        "scripts/indicators.py": "preserve_public",
        "chat-bot-bridge/server.js": "sanitize_required",
        "scripts/analysis/indicators.py": "reusable_candidate",
        "unknown/new.txt": "manual_review",
    }
    for rel, expected in cases.items():
        actual, _ = classify(rel, rules, policy["default_class"])
        if actual != expected:
            print(f"self-test failed: {rel} -> {actual}, expected {expected}", file=sys.stderr)
            return 1
    if normalize_remote("https://github.com/Org/Repo.git") != normalize_remote("https://github.com/org/repo"):
        print("self-test failed: remote normalization", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "chat-bot-bridge").mkdir()
        (root / "chat-bot-bridge" / ".env.example").write_text(
            "TELEGRAM_BOT_TOKEN=\n", encoding="utf-8"
        )
        errors: list[str] = []
        check_env_example(root, {"secret_env_keys": ["TELEGRAM_BOT_TOKEN"]}, errors)
        if errors:
            print("self-test failed: blank env key rejected", file=sys.stderr)
            return 1
        (root / "chat-bot-bridge" / ".env.example").write_text(
            "TELEGRAM_BOT_TOKEN=secret\n", encoding="utf-8"
        )
        check_env_example(root, {"secret_env_keys": ["TELEGRAM_BOT_TOKEN"]}, errors)
        if not errors:
            print("self-test failed: populated env secret accepted", file=sys.stderr)
            return 1
    if shutil.which("git"):
        with tempfile.TemporaryDirectory() as td:
            source, target = Path(td) / "source", Path(td) / "target"
            for repo in (source, target):
                repo.mkdir()
                subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
                subprocess.run(
                    ["git", "-C", str(repo), "remote", "add", "origin",
                     "https://example.invalid/owner/shared.git"], check=True,
                )
            report = compare(source, target, policy, False, [])
            if not any("share a git remote" in error for error in report["errors"]):
                print("self-test failed: shared remote was not blocked", file=sys.stderr)
                return 1
    print("✅ sync_audit self-test passed")
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, help="source checkout/worktree to audit")
    ap.add_argument("--target", type=Path, default=ROOT,
                    help="public target checkout (default: this repository)")
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--denylist", action="append", type=Path, default=[],
                    help="additional local literal denylist; repeatable")
    ap.add_argument("--explain", metavar="PATH",
                    help="classify one repository-relative path and exit")
    ap.add_argument("--allow-shared-repository", action="store_true",
                    help="acknowledge reduced isolation for two worktrees of one git repository")
    ap.add_argument("--json", action="store_true", help="print the full machine-readable report")
    ap.add_argument("--limit", type=int, default=100, help="maximum text-mode difference rows")
    ap.add_argument("--fail-on-review", action="store_true",
                    help="exit 2 when review candidates remain, even if safety checks pass")
    ap.add_argument("--self-test", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_policy(args.policy.resolve())
    if args.self_test:
        return self_test(policy)
    if args.explain:
        name, action = classify(
            args.explain, compiled_classes(policy), policy["default_class"]
        )
        result = {"path": args.explain, "class": name, "action": action,
                  "policy_id": policy["policy_id"],
                  "policy_version": policy["policy_version"]}
        print(json.dumps(result, indent=2) if args.json else
              f"{args.explain}: {name}\n{action}")
        return 0
    if not args.source:
        print("--source is required unless --self-test or --explain is used", file=sys.stderr)
        return 2
    source, target = args.source.resolve(), args.target.resolve()
    if not source.is_dir() or not target.is_dir():
        print("source and target must be existing directories", file=sys.stderr)
        return 2
    if source == target:
        print("source and target must be different directories", file=sys.stderr)
        return 2

    report = compare(
        source, target, policy, args.allow_shared_repository,
        [p.expanduser().resolve() for p in args.denylist],
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text(report, max(1, args.limit))
    if report["errors"]:
        return 1
    if args.fail_on_review and any(
        row["disposition"] in {"review_candidate", "manual_sanitization", "manual_classification"}
        for row in report["differences"]
    ):
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Normal when a reviewer pipes JSON/text into a selector that exits early.
        try:
            sys.stdout.close()
        finally:
            raise SystemExit(0)
