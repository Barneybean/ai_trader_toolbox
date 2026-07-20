# Channel Mining (followed channels → transcripts → underwritten lenses)

The desk can turn finance channels the user follows (mentors, analysts, market commentators on YouTube) into two inputs: a **transcript library** on disk (timestamped Markdown per video, organized by channel), and **distilled method lenses** that survive conflict review. Transcripts are evidence to underwrite, never signals to copy — any name a channel pitches is a candidate for the full pipeline, not a call.

## Acquiring transcripts

The open-source [YouTube Transcriber](https://github.com/Barneybean/youtube-transcriber) service runs locally (default `localhost:19720`) and exports channel batches: YouTube captions first, then any configured cloud Whisper, local Whisper last; members-only videos can use the signed-in Chrome profile; re-runs skip existing files. CLI wrapper (logs via desk_log):

    python3 scripts/ops/transcribe_channel.py start <channel-URL> [--year 2026]   # batch export
    python3 scripts/ops/transcribe_channel.py watch                               # poll to completion
    python3 scripts/ops/transcribe_channel.py video <url> [--lang zh-Hans,en]     # one video, into the library DB

If the service is down the wrapper prints the start command. Export root is set by the service's `YTT_EXPORT_ROOT` env var; keep it **outside this repo** — transcripts are personal knowledge, never committed.

**When to pull:** (a) a followed channel publishes on a held name or an open premise — fetch the video same-day and check it against the open book (information only / premise hit / must-act); (b) periodic top-up of a mined channel (re-run `start`, duplicates skip); (c) before underwriting a pick heard second-hand, pull the source video — argue with the primary claim, not a summary.

## Distilling transcripts → desk lenses

Batch-mining a channel:

1. **Read in bulk, extract candidate tells** — recurring, falsifiable claims with stated triggers; drop vibes, predictions without mechanism, and anything requiring the author's discretion to apply.
2. **Conflict review before anything lands** — for each candidate: duplicate of an existing skill → reject (note the file it duplicates); contradicts an accepted ADR or a standing mentor rule → reject or escalate to the user, never silently adopt; genuinely new → keep.
3. **Land as expiring hypotheses, not gates** — new tells enter the insight registry (`skills/decision/insight-registry.md`): regime-tagged, scored out-of-sample. Only survivors earn skill-file space; a distilled method file cites its source channel and date.
4. **Names mentioned are candidates, not calls** — route through the full pipeline (`skills/decision/sufficiency-gate.md`, `skills/analysis/valuation-quality-gate.md`, roles). Underwrite, never chase — especially for channels with a large audience, where the pick may already be reflexively priced.

## Boundaries

- Transcript files and the transcriber's database stay outside this repo; reports may cite a channel/video by name + date.
- Channel opinions never bypass the sufficiency gate or substitute for primary sources (filings, the *company's* own call transcripts).
