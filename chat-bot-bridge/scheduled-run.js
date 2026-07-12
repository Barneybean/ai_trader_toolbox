#!/usr/bin/env node
/**
 * Scheduled desk runs — launchd fires this weekdays:
 *   node scheduled-run.js premarket    (5:45 AM PT, before the 6:30 open)
 *   node scheduled-run.js postmarket   (1:15 PM PT, after the 1:00 close)
 *   node scheduled-run.js test         (plumbing check, trivial prompt)
 *
 * Runs claude headless in the desk repo with the same house rules as the
 * chat bridge (chat-rules.js, trading mode injected), then delivers the
 * reply + any FILE: attachments to the phone over Telegram. On success the
 * run's session id is written to state.json so a phone reply ("approve 1")
 * resumes THIS session with the report context.
 *
 * Zero dependencies, same as server.js.
 */

import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { chatRulesBase, modeRules, currentMode } from './chat-rules.js';

const BRIDGE_DIR = path.dirname(fileURLToPath(import.meta.url));
const DESK_DIR = path.resolve(BRIDGE_DIR, '..');
const STATE_FILE = path.join(BRIDGE_DIR, 'state.json');
const SETTINGS_FILE = path.join(BRIDGE_DIR, 'claude-settings.json');
const ACTIVITY_LOG = path.join(BRIDGE_DIR, 'logs', 'activity.jsonl');
const CLAUDE_BIN = process.env.CLAUDE_BIN || 'claude';
const TIMEOUT_MS = 45 * 60 * 1000; // full desk runs are long; cap at 45 min

// .env loader (same as server.js)
for (const line of (() => { try { return fs.readFileSync(path.join(BRIDGE_DIR, '.env'), 'utf8').split('\n'); } catch { return []; } })()) {
  const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
  if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
}
const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_ALLOWED_USER_ID;
if (!TOKEN || !CHAT_ID) { console.error('missing telegram config in .env'); process.exit(1); }

const log = (...a) => console.log(new Date().toISOString(), ...a);
function logEvent(event, data = {}) {
  try {
    fs.mkdirSync(path.dirname(ACTIVITY_LOG), { recursive: true });
    fs.appendFileSync(ACTIVITY_LOG,
      JSON.stringify({ ts: new Date().toISOString(), component: 'scheduled', event, ...data }) + '\n');
  } catch { /* never fail on logging */ }
}

async function tg(method, payload) {
  const res = await fetch(`https://api.telegram.org/bot${TOKEN}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  return res.json();
}
async function sendText(text) {
  for (let i = 0; i < text.length; i += 3900) {
    await tg('sendMessage', { chat_id: Number(CHAT_ID), text: text.slice(i, i + 3900) });
  }
}
async function sendFile(p, caption = '') {
  const form = new FormData();
  form.append('chat_id', CHAT_ID);
  if (caption) form.append('caption', caption);
  form.append('document', new Blob([fs.readFileSync(p)], { type: 'text/html' }), path.basename(p));
  const res = await fetch(`https://api.telegram.org/bot${TOKEN}/sendDocument`, { method: 'POST', body: form });
  return (await res.json()).ok;
}

// FILE: directive extraction — same guards as server.js
function extractFileDirectives(reply) {
  const files = [];
  const lines = String(reply).split('\n').filter((line) => {
    const m = line.match(/^\s*FILE:\s*(\/\S.*?)\s*$/);
    if (!m) return true;
    const p = path.resolve(m[1]);
    const inDesk = p.startsWith(DESK_DIR + path.sep);
    const inBridge = p.startsWith(BRIDGE_DIR + path.sep);
    const hidden = p.split(path.sep).some((seg) => seg.startsWith('.'));
    try {
      const st = fs.statSync(p);
      if (inDesk && !inBridge && !hidden && st.isFile() && st.size < 45 * 1024 * 1024) files.push(p);
    } catch { /* missing file — drop the directive */ }
    return false;
  });
  return { text: lines.join('\n').trim(), files };
}

const MODE_TASK = {
  full: 'FULL-AUTO: after the report, execute playbook-compliant tickets only in the configured execution account and include each fill + rationale.',
  semi: 'SEMI-AUTO: end with numbered proposed tickets so the user can reply "approve N".',
  manual: 'MANUAL: advise only; no tickets are executed from this run.',
};

function buildPrompt(kind, mode) {
  if (kind === 'test') return 'This is a scheduled-run plumbing test. Reply with exactly: scheduled-run test ok';
  const common = `${MODE_TASK[mode]}\nBuild the bilingual HTML report, commit it per repo convention, and attach it with a FILE: line. Reply with the TLDR only.`;
  if (kind === 'premarket') {
    return `Scheduled PRE-MARKET complete daily report (${new Date().toDateString()}). "Daily" means the full decision-grade SKILL.md pipeline, not a summary: cover the portfolio, open decisions/orders, alerts/levels, material watchlist changes and qualified outside opportunities; recall history first; collect enough fresh dated data and supporting evidence; run all relevant roles, engines, debates and gates; build the full bilingual HTML report. Include overnight/pre-market moves, today's catalyst calendar and execution-ready plan. ${common}`;
  }
  return `Scheduled POST-MARKET complete daily report (${new Date().toDateString()}). "Daily" means the full decision-grade SKILL.md pipeline, not a summary: cover every holding and actionable candidate with enough fresh dated data and supporting evidence, recall history first, run all relevant roles, engines, debates and gates, and build the full bilingual HTML report. Review how the book and today's plan printed, score resolved calls, explain key closes/after-hours moves, and set tomorrow's levels and execution-ready plan. ${common}`;
}

async function main() {
  const kind = process.argv[2];
  if (!['premarket', 'postmarket', 'test'].includes(kind)) {
    console.error('usage: scheduled-run.js premarket|postmarket|test');
    process.exit(2);
  }
  // weekend guard (launchd Weekday filter already handles this; belt+suspenders
  // for manual runs — 'test' is exempt)
  const dow = new Date().getDay();
  if (kind !== 'test' && (dow === 0 || dow === 6)) { log('weekend — skipping'); return; }

  const mode = currentMode();
  const label = kind === 'premarket' ? '🌅 Pre-market' : kind === 'postmarket' ? '🌇 Post-market' : '🔧 Test';
  log(`${kind} run starting (mode: ${mode})`);
  logEvent('scheduled_start', { kind, mode });
  if (kind !== 'test') await sendText(`${label} run starting (mode: ${mode}) — report lands here when done.`);

  const startMs = Date.now();
  const result = await new Promise((resolve) => {
    const child = spawn(CLAUDE_BIN, [
      '-p', buildPrompt(kind, mode),
      '--output-format', 'stream-json', '--verbose',
      '--settings', SETTINGS_FILE,
      '--append-system-prompt', chatRulesBase(),
      '--append-system-prompt', modeRules(mode),
    ], {
      cwd: DESK_DIR,
      stdio: ['ignore', 'pipe', 'pipe'], // no stdin — stops the CLI's 3s stdin wait/warning
      env: { ...process.env, PATH: `${process.env.HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin` },
    });
    let buf = '', err = '', res = null;
    const timer = setTimeout(() => { child.kill('SIGTERM'); setTimeout(() => child.kill('SIGKILL'), 10_000); }, TIMEOUT_MS);
    child.stdout.on('data', (d) => {
      buf += d;
      let nl;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        try { const ev = JSON.parse(line); if (ev.type === 'result') res = ev; } catch { /* partial line */ }
      }
    });
    child.stderr.on('data', (d) => { err += d; if (err.length > 20_000) err = err.slice(-10_000); });
    child.on('error', (e) => { clearTimeout(timer); resolve({ ok: false, text: `could not start claude (${e.message})` }); });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (res) resolve({ ok: !res.is_error, text: String(res.result || res.error || '(empty reply)'), sessionId: res.session_id, costUsd: res.total_cost_usd });
      else resolve({ ok: false, text: `claude exited (code ${code}) without a result.\n${err.trim().slice(-1200) || '(no output)'}` });
    });
  });

  const durationMin = Math.round((Date.now() - startMs) / 60_000);
  logEvent('scheduled_done', { kind, mode, ok: result.ok, duration_min: durationMin, cost_usd: result.costUsd });

  if (!result.ok) {
    await sendText(`⚠️ ${label} run FAILED after ${durationMin}m:\n${result.text.slice(0, 2500)}`);
    process.exit(1);
  }

  // hand the session to the bridge so a phone reply ("approve 1") has context
  if (result.sessionId && kind !== 'test') {
    try {
      const state = (() => { try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch { return {}; } })();
      state.sessionId = result.sessionId;
      fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
    } catch (e) { log('state handoff failed:', e.message); }
  }

  const { text, files } = extractFileDirectives(result.text);
  if (text) await sendText(text);
  for (const f of files) {
    const ok = await sendFile(f);
    log(ok ? `sent file: ${f}` : `FILE SEND FAILED: ${f}`);
    logEvent('file_sent', { kind, file: f, ok });
  }
  log(`${kind} run done in ${durationMin}m`);
}

main().catch(async (e) => {
  logEvent('scheduled_crash', { error: String(e?.message || e) });
  try { await sendText(`⚠️ Scheduled run crashed: ${e?.message || e}`); } catch { /* offline */ }
  process.exit(1);
});
