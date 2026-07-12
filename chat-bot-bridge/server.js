#!/usr/bin/env node
/**
 * Chat-bot bridge for the trading desk — phone messenger in, Claude Code out.
 * Multi-provider, all official; auto-detected from .env credentials
 * (precedence provider priority order configured by the user) or forced with PROVIDER=...:
 *   - telegram: Bot API long-polling (current; free, no tunnel, near-instant)
 *   - twilio:   Twilio WhatsApp API (polling or webhook mode)
 *   - meta:     WhatsApp Business Cloud API (webhook + Graph API)
 *   - discord:  Discord Bot API polling (no public webhook or npm dependency)
 *
 * Zero npm dependencies: Node built-ins (http, crypto) + global fetch only.
 *
 * Security model:
 *  - Only the allowlisted sender is obeyed (TELEGRAM_ALLOWED_USER_ID /
 *    ALLOWED_WA_ID); everyone else is logged and ignored.
 *  - Webhook modes require a valid provider signature — X-Twilio-Signature
 *    (HMAC-SHA1 of PUBLIC_URL + sorted params) or X-Hub-Signature-256
 *    (HMAC-SHA256 of the raw body). Anything else -> 401. Polling modes have
 *    no inbound surface at all (outbound HTTPS only).
 *  - Claude runs headless (`claude -p --resume`) in the ai-trader-toolbox repo with
 *    the permission settings in claude-settings.json and the chat house rules
 *    appended to its system prompt (order confirm flow, account masking,
 *    FILE: attachment directives).
 *  - Secrets live in .env (git-ignored). See .env.example.
 */

import http from 'http';
import https from 'https';
import crypto from 'crypto';
import dns from 'dns';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { chatRulesBase, modeRules, currentMode, setMode, MODES } from './chat-rules.js';
import { CODEX_UNAVAILABLE_RE, codexAvailabilityError } from './agent-routing.js';

// Some macOS/Wi-Fi combinations advertise an IPv6 route that black-holes
// Telegram traffic. Node's fetch can then sit in the OS connect path for many
// minutes. Prefer IPv4 for all lookups; telegramApi below also forces family 4.
dns.setDefaultResultOrder('ipv4first');

// ---------------------------------------------------------------- config ---
const BRIDGE_DIR = path.dirname(fileURLToPath(import.meta.url));
const DESK_DIR = path.resolve(BRIDGE_DIR, '..');
const STATE_FILE = path.join(BRIDGE_DIR, 'state.json');
const SETTINGS_FILE = path.join(BRIDGE_DIR, 'claude-settings.json');

// minimal .env loader (no dotenv dependency)
try {
  for (const line of fs.readFileSync(path.join(BRIDGE_DIR, '.env'), 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
} catch { /* .env optional if real env vars are set */ }

const {
  // telegram provider (Bot API, long-polling — no tunnel, free)
  TELEGRAM_BOT_TOKEN,       // from @BotFather
  TELEGRAM_ALLOWED_USER_ID, // YOUR numeric Telegram user id — the only allowed sender
  // discord provider (Bot REST API polling — no gateway or public listener)
  DISCORD_BOT_TOKEN,
  DISCORD_ALLOWED_USER_ID,
  DISCORD_CHANNEL_ID,
  // whatsapp shared
  ALLOWED_WA_ID,         // YOUR phone in digits-only form e.g. 14155551234
  // twilio provider
  TWILIO_ACCOUNT_SID,    // ACxxxxxxxx from the Twilio console dashboard
  TWILIO_AUTH_TOKEN,     // auth token from the same page (also signs webhooks)
  TWILIO_WHATSAPP_FROM,  // e.g. whatsapp:+14155238886 (the sandbox number)
  PUBLIC_URL,            // exact public webhook URL, e.g. https://x.ngrok-free.app/webhook
  // meta provider
  WHATSAPP_TOKEN,        // system-user token w/ whatsapp_business_messaging
  PHONE_NUMBER_ID,       // the business/test number's ID (not the number itself)
  APP_SECRET,            // Meta app secret — validates webhook signatures
  VERIFY_TOKEN,          // any string you choose; must match Meta webhook config
} = process.env;
const PROVIDER_PRIORITY = (process.env.PROVIDER_PRIORITY || 'telegram,discord,twilio,meta')
  .split(',').map(x => x.trim()).filter(Boolean);
const PROVIDER_CONFIGURED = {
  telegram: Boolean(TELEGRAM_BOT_TOKEN),
  discord: Boolean(DISCORD_BOT_TOKEN),
  twilio: Boolean(TWILIO_ACCOUNT_SID),
  meta: Boolean(WHATSAPP_TOKEN),
};
const PROVIDER = process.env.PROVIDER ||
  PROVIDER_PRIORITY.find(name => PROVIDER_CONFIGURED[name]) || PROVIDER_PRIORITY[0] || 'telegram';
const PORT = Number(process.env.PORT || 3000);
const GRAPH_VERSION = process.env.GRAPH_VERSION || 'v23.0';
const CLAUDE_BIN = process.env.CLAUDE_BIN || 'claude';
const CODEX_BIN = process.env.CODEX_BIN || 'codex';
const AGENT_PRIORITY = (process.env.AGENT_PRIORITY || 'codex,claude').split(',').map(x => x.trim()).filter(Boolean);
const CODEX_MODEL = process.env.CODEX_MODEL || 'default';
const CLAUDE_MODEL = process.env.CLAUDE_MODEL || 'default';
// full desk runs + report builds regularly pass 30 min; killed runs lose the
// whole result (seen 2026-07-11: META report SIGTERMed at the old 30-min cap)
const CLAUDE_TIMEOUT_MS = Number(process.env.CLAUDE_TIMEOUT_MIN || 60) * 60 * 1000;
const CODEX_TIMEOUT_MS = Number(process.env.CODEX_TIMEOUT_MIN || 60) * 60 * 1000;
// WhatsApp/Telegram cap text at 4096; Twilio splits >1600 itself but cleaner to chunk ourselves
// twilio runs in webhook mode when PUBLIC_URL is set, else POLLING mode:
// pull inbound messages from the Twilio API over outbound HTTPS — no tunnel,
// no inbound exposure, ~POLL_MS reply latency.
const TWILIO_POLLING = PROVIDER === 'twilio' && !PUBLIC_URL;
const POLL_MS = Number(process.env.POLL_MS || 3000);

const SUPPORTED_PROVIDERS = ['telegram', 'discord', 'twilio', 'meta'];
if (!SUPPORTED_PROVIDERS.includes(PROVIDER)) {
  console.error(`Unknown PROVIDER=${PROVIDER}. Supported: ${SUPPORTED_PROVIDERS.join(', ')}`);
  process.exit(1);
}
const required =
  PROVIDER === 'telegram' ? { TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_ID }
  : PROVIDER === 'discord' ? { DISCORD_BOT_TOKEN, DISCORD_ALLOWED_USER_ID, DISCORD_CHANNEL_ID }
  : PROVIDER === 'twilio' ? { ALLOWED_WA_ID, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM }
  : { ALLOWED_WA_ID, WHATSAPP_TOKEN, PHONE_NUMBER_ID, APP_SECRET, VERIFY_TOKEN };
// the one identity allowed to drive the desk, regardless of provider
const ALLOWED_SENDER = PROVIDER === 'telegram' ? TELEGRAM_ALLOWED_USER_ID
  : PROVIDER === 'discord' ? DISCORD_ALLOWED_USER_ID : ALLOWED_WA_ID;
const missing = Object.entries(required).filter(([, v]) => !v).map(([k]) => k);
if (missing.length) {
  console.error(`[${PROVIDER} mode] Missing required config: ${missing.join(', ')} — see .env.example.`);
  process.exit(1);
}

// house rules now live in chat-rules.js (shared with scheduled-run.js) and
// are rebuilt per run so a /mode switch applies to the very next message

// ------------------------------------------------------------- state -------
function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch { return {}; }
}
function saveState(s) { fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2)); }
let state = loadState(); // separate provider sessions + shared last-run metadata
if (state.sessionId && !state.claudeSessionId) state.claudeSessionId = state.sessionId; // migrate v2

// --- session rotation: resuming one session forever replays an ever-growing
// transcript on EVERY message (seen 2026-07-11: a 927KB session made each
// phone message cost ~a full context of input tokens and runs slow to the
// point of timing out). Rotate to a fresh session when the transcript gets
// big or the conversation has gone stale.
const PROJECT_DIR = path.join(process.env.HOME, '.claude', 'projects', DESK_DIR.replace(/[^a-zA-Z0-9]/g, '-'));
const MAX_SESSION_KB = Number(process.env.MAX_SESSION_KB || 300);
const MAX_SESSION_IDLE_H = Number(process.env.MAX_SESSION_IDLE_H || 6);

function sessionTranscriptKB() {
  if (!state.claudeSessionId) return 0;
  try { return Math.round(fs.statSync(path.join(PROJECT_DIR, `${state.claudeSessionId}.jsonl`)).size / 1024); }
  catch { return 0; }
}

function agentLabel(agent, model) {
  const pretty = agent === 'codex' ? 'Codex' : agent === 'claude' ? 'Claude' : String(agent || 'unknown');
  return model ? `${pretty} (${model})` : pretty;
}

function compactHistory(history) {
  if (!Array.isArray(history) || history.length === 0) return '';
  const tail = history.slice(-2);
  return tail.map((item) => {
    const role = item?.role === 'assistant' ? 'Assistant' : 'User';
    const text = String(item?.text || '').replace(/\s+/g, ' ').trim().slice(0, role === 'Assistant' ? 900 : 500);
    return `${role}: ${text}`;
  }).join('\n');
}

function handoffPrompt({ from, to, reason, prompt, history, restart = false }) {
  const recent = compactHistory(history);
  const context = recent ? `Recent phone context:\n${recent}\n\n` : '';
  const transition = restart
    ? 'The previous agent could not continue cleanly. Restart from the original prompt below.'
    : 'Continue from the last completed step. Preserve completed work and do not repeat finished analysis unless needed to recover context.';
  return [
    `Agent handoff from ${agentLabel(from.name, from.model)} to ${agentLabel(to.name, to.model)}.`,
    `Reason: ${reason}.`,
    transition,
    `${context}Original prompt:\n${prompt}`,
  ].join('\n\n');
}

function rotateSessionIfNeeded() {
  if (!state.claudeSessionId && !state.codexSessionId) return null;
  let reason = null;
  if (state.lastRunAt && Date.now() - state.lastRunAt > MAX_SESSION_IDLE_H * 3600_000) reason = 'idle';
  const kb = sessionTranscriptKB();
  if (kb > MAX_SESSION_KB) reason = reason || 'size';
  if (reason) {
    state.claudeSessionId = null;
    state.codexSessionId = null;
    saveState(state);
  }
  return reason;
}

const log = (...a) => console.log(new Date().toISOString(), ...a);

// structured activity events → logs/activity.jsonl (debugging + reliability
// audit trail; the text log above stays the human-readable stream)
const ACTIVITY_LOG = path.join(BRIDGE_DIR, 'logs', 'activity.jsonl');
function logEvent(event, data = {}) {
  try {
    fs.mkdirSync(path.dirname(ACTIVITY_LOG), { recursive: true });
    try { // rotate at 10 MB so the file never grows unbounded
      if (fs.statSync(ACTIVITY_LOG).size > 10 * 1024 * 1024) {
        fs.renameSync(ACTIVITY_LOG, ACTIVITY_LOG + '.1');
      }
    } catch { /* no file yet */ }
    fs.appendFileSync(ACTIVITY_LOG,
      JSON.stringify({ ts: new Date().toISOString(), component: 'bridge', event, ...data }) + '\n');
  } catch { /* logging must never take the bridge down */ }
}

// per-message latency breakdown → logs/timing.jsonl (one line per prompt;
// legs are seconds relative to bridge receipt, phone_to_bridge_s from the
// provider's sent timestamp when it supplies one)
const TIMING_LOG = path.join(BRIDGE_DIR, 'logs', 'timing.jsonl');
function logTiming(rec) {
  try {
    fs.appendFileSync(TIMING_LOG, JSON.stringify({ ts: new Date().toISOString(), ...rec }) + '\n');
  } catch { /* never take the bridge down */ }
}

// ------------------------------------------------------------ claude -------
// Streams claude's output (--output-format stream-json) so the bridge can
// notify the phone the moment things happen instead of after the run ends:
//   onEvent('started')          — the agent process is up and working
//   onEvent('trouble', detail)  — rate limit / fetch failure / network error
//                                 seen mid-run (throttled: ≥2 min apart, ≤3/run)
const TROUBLE_RE = /rate.?limit|too many requests|overloaded|quota exceeded|\b429\b|\b529\b|fetch failed|failed to fetch|ETIMEDOUT|ECONNRESET|ECONNREFUSED|ENOTFOUND|network error|API Error/i;

function runClaude(prompt, onEvent = () => {}) {
  return new Promise((resolve) => {
    const args = [
      '-p', prompt,
      '--output-format', 'stream-json',
      '--verbose',
      '--settings', SETTINGS_FILE,
      ...(CLAUDE_MODEL === 'default' ? [] : ['--model', CLAUDE_MODEL]),
      '--append-system-prompt', chatRulesBase(),
      '--append-system-prompt', modeRules(currentMode()),
    ];
    if (state.claudeSessionId) args.push('--resume', state.claudeSessionId);

    const child = spawn(CLAUDE_BIN, args, {
      cwd: DESK_DIR,
      stdio: ['ignore', 'pipe', 'pipe'], // no stdin — stops the CLI's 3s stdin wait/warning
      env: {
        ...process.env,
        PATH: `${process.env.HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`,
      },
    });

    let buf = '', err = '', result = null, started = false, timedOut = false;
    let fallbackRequested = false, fallbackReason = null;
    let lastTroubleMs = 0, troubleCount = 0;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGTERM');
      setTimeout(() => child.kill('SIGKILL'), 10_000);
    }, CLAUDE_TIMEOUT_MS);

    const reportTrouble = (detail) => {
      const now = Date.now();
      if (now - lastTroubleMs < 120_000 || troubleCount >= 3) return;
      lastTroubleMs = now; troubleCount++;
      onEvent('trouble', String(detail).replace(/\s+/g, ' ').trim().slice(0, 300));
    };

    child.stdout.on('data', (d) => {
      buf += d;
      let nl;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        let ev;
        try { ev = JSON.parse(line); } catch { continue; }
        if (!started) { started = true; onEvent('started', { agent: 'claude', model: CLAUDE_MODEL }); }
        if (ev.type === 'result') { result = ev; continue; }
        // the CLI reports usage-limit state as a first-class event
        if (ev.type === 'rate_limit_event') {
          const ri = ev.rate_limit_info;
          if (ri && ri.status && ri.status !== 'allowed') {
            const resets = ri.resetsAt ? ` — resets ${new Date(ri.resetsAt * 1000).toLocaleString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}` : '';
            fallbackRequested = true;
            fallbackReason = `usage limit: ${ri.status}${resets}`;
            reportTrouble(`Claude usage limit: ${ri.status}${resets}`);
            child.kill('SIGTERM');
          }
          continue;
        }
        // FAILED tool calls (yahoo fetch, web search, MCP) — surface right
        // away. is_error gate matters: successful tool output can quote these
        // words legitimately (seen 2026-07-11: the agent Read this very file
        // and the TROUBLE_RE source line was texted to the phone as trouble)
        if (ev.type === 'user') {
          for (const c of ev.message?.content || []) {
            if (c.type !== 'tool_result' || c.is_error !== true) continue;
            const t = typeof c.content === 'string' ? c.content : JSON.stringify(c.content ?? '');
            if (TROUBLE_RE.test(t)) reportTrouble(t.match(/[^"\\]*(?:rate.?limit|429|529|fetch failed|failed to fetch|ETIMEDOUT|ECONNRESET|ENOTFOUND|too many requests|overloaded)[^"\\]*/i)?.[0] || t);
          }
        }
      }
    });
    child.stderr.on('data', (d) => {
      err += d;
      if (err.length > 20_000) err = err.slice(-10_000);
      const s = String(d);
      // the CLI prints API retry errors (429/529, network) to stderr
      if (TROUBLE_RE.test(s)) reportTrouble(s.split('\n').find((l) => TROUBLE_RE.test(l)) || s);
    });
    child.on('error', (e) => {
      clearTimeout(timer);
      resolve({ ok: false, agent: 'claude', fallbackEligible: true,
        model: CLAUDE_MODEL, switchReason: `could not start Claude (${e.message})`,
        text: `bridge error: could not start Claude (${e.message})` });
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (result) {
        if (result.session_id) { state.claudeSessionId = result.session_id; }
        state.lastRunAt = Date.now();
        saveState(state);
        const text = result.result || result.error || '(empty reply)';
        const u = result.usage || {};
        resolve({
          ok: !result.is_error,
          text: String(text),
          costUsd: result.total_cost_usd,
          agent: 'claude', model: result.model || CLAUDE_MODEL, fallbackEligible: false, tokens: {
            in: u.input_tokens, out: u.output_tokens,
            cache_read: u.cache_read_input_tokens, cache_write: u.cache_creation_input_tokens,
          },
        });
      } else if (timedOut) {
        resolve({ ok: false, agent: 'claude', model: CLAUDE_MODEL, fallbackEligible: false, text: `run hit the ${Math.round(CLAUDE_TIMEOUT_MS / 60_000)}-min bridge limit and was stopped — the work up to that point is saved in the session; send a follow-up to resume/finish it.` });
      } else if (fallbackRequested) {
        resolve({ ok: false, agent: 'claude', model: CLAUDE_MODEL, fallbackEligible: true, switchReason: fallbackReason || 'usage limit reached', text: `Claude hit a usage limit and was stopped so the bridge can switch agents.` });
      } else {
        const tail = err.trim().slice(-1500);
        resolve({ ok: false, agent: 'claude', model: CLAUDE_MODEL, fallbackEligible: false, text: `claude exited (code ${code}) without a result.\n${tail || '(no output)'}` });
      }
    });
  });
}

function runCodex(prompt, onEvent = () => {}) {
  return new Promise((resolve) => {
    const phonePrompt = `${prompt}\n\n${chatRulesBase()}\n${modeRules(currentMode())}`;
    const common = ['--json'];
    const modelArgs = CODEX_MODEL === 'default' ? [] : ['--model', CODEX_MODEL];
    const args = state.codexSessionId
      ? ['exec', 'resume', ...common, ...modelArgs, '-c', 'sandbox_mode="workspace-write"', state.codexSessionId, phonePrompt]
      : ['exec', ...common, ...modelArgs, '--sandbox', 'workspace-write', '--cd', DESK_DIR, phonePrompt];
    const child = spawn(CODEX_BIN, args, {
      cwd: DESK_DIR, stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PATH: `${process.env.HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin` },
    });
    let buf = '', err = '', eventTail = '', availabilityError = '', finalText = '', sessionId = null, usage = null;
    let started = false, timedOut = false, settled = false;
    const finish = (value) => { if (settled) return; settled = true; resolve(value); };
    const timer = setTimeout(() => { timedOut = true; child.kill('SIGTERM'); setTimeout(() => child.kill('SIGKILL'), 10_000); }, CODEX_TIMEOUT_MS);
    child.stdout.on('data', (d) => {
      buf += d; let nl;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
        let ev; try { ev = JSON.parse(line); } catch { continue; }
        eventTail = (eventTail + '\n' + line).slice(-6000);
        if (!started) { started = true; onEvent('started', { agent: 'codex', model: CODEX_MODEL }); }
        if (ev.type === 'thread.started') sessionId = ev.thread_id || ev.thread?.id || sessionId;
        if (ev.type === 'item.completed' && ev.item?.type === 'agent_message') finalText = ev.item.text || finalText;
        if (ev.type === 'turn.completed') usage = ev.usage || usage;
        const unavailable = codexAvailabilityError(ev);
        if (unavailable) {
          availabilityError = unavailable;
          onEvent('trouble', `Codex availability: ${unavailable.slice(0, 250)}`);
        }
      }
    });
    child.stderr.on('data', (d) => { err += d; if (err.length > 20_000) err = err.slice(-10_000); });
    child.on('error', (e) => { clearTimeout(timer); finish({ ok: false, agent: 'codex', model: CODEX_MODEL, fallbackEligible: true, switchNotified: true, switchReason: `could not start Codex (${e.message})`, text: `could not start Codex (${e.message})` }); });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (finalText) {
        if (sessionId) state.codexSessionId = sessionId;
        state.lastRunAt = Date.now(); state.lastAgent = 'codex'; saveState(state);
        finish({ ok: true, agent: 'codex', fallbackEligible: false, text: finalText,
                 model: CODEX_MODEL,
                 tokens: usage ? { in: usage.input_tokens, out: usage.output_tokens,
                   cache_read: usage.cached_input_tokens } : undefined });
      } else {
        const detail = (err || eventTail || buf).trim().slice(-1500) || `Codex exited ${code} without a final message`;
        const unavailable = (availabilityError || err).trim();
        finish({ ok: false, agent: 'codex', fallbackEligible: !timedOut && (code !== 0 || Boolean(unavailable && CODEX_UNAVAILABLE_RE.test(unavailable))),
                 model: CODEX_MODEL,
                 switchNotified: Boolean(unavailable && CODEX_UNAVAILABLE_RE.test(unavailable)),
                 switchReason: unavailable && CODEX_UNAVAILABLE_RE.test(unavailable) ? unavailable.slice(-1500) : null,
                 text: timedOut ? `Codex hit the ${Math.round(CODEX_TIMEOUT_MS / 60_000)}-minute bridge limit.` : detail });
      }
    });
  });
}

async function runPreferredAgent(prompt, onEvent = () => {}) {
  const runners = { codex: runCodex, claude: runClaude };
  const preference = state.agentPreference || 'auto';
  const order = preference === 'auto' ? AGENT_PRIORITY : [preference];
  let last = { ok: false, text: 'No configured agent is available.' };
  let restartAfterSwitch = false;
  let lastAttempt = state.lastAgent ? { name: state.lastAgent, model: state.lastAgent === 'codex' ? CODEX_MODEL : CLAUDE_MODEL } : null;
  for (const name of order) {
    const runner = runners[name];
    if (!runner) continue;
    const history = Array.isArray(state.recentHistory) ? state.recentHistory.slice(-8) : [];
    const routedPrompt = lastAttempt && lastAttempt.name !== name && history.length
      ? handoffPrompt({
        from: lastAttempt,
        to: { name, model: name === 'codex' ? CODEX_MODEL : CLAUDE_MODEL },
        reason: last.switchReason || 'previous agent ended early',
        prompt,
        history,
        restart: restartAfterSwitch,
      })
      : prompt;
    last = await runner(routedPrompt, onEvent);
    lastAttempt = { name: last.agent || name, model: last.model || (name === 'codex' ? CODEX_MODEL : CLAUDE_MODEL) };
    if (last.ok || !last.fallbackEligible) return last;
    const next = order.slice(order.indexOf(name) + 1).find(x => runners[x]);
    if (next) {
      const toModel = next === 'codex' ? CODEX_MODEL : CLAUDE_MODEL;
      const reason = last.switchReason || last.text || 'agent unavailable';
      log(`agent fallback: ${name} -> ${next}: ${String(last.text).slice(0, 180)}`);
      logEvent('agent_fallback', { from: name, to: next, reason: String(last.text).slice(0, 500) });
      if (!last.switchNotified) {
        onEvent('switch', {
          from: { name, model: last.model || (name === 'codex' ? CODEX_MODEL : CLAUDE_MODEL) },
          to: { name: next, model: toModel },
          reason,
          restart: restartAfterSwitch,
        });
      }
      restartAfterSwitch = false;
    }
  }
  return last;
}

// ---------------------------------------------------------- providers ------
function chunkText(text, maxChars) {
  const chunks = [];
  let rest = String(text);
  while (rest.length > maxChars) {
    let cut = rest.lastIndexOf('\n\n', maxChars);
    if (cut < maxChars * 0.5) cut = rest.lastIndexOf('\n', maxChars);
    if (cut < maxChars * 0.5) cut = maxChars;
    chunks.push(rest.slice(0, cut));
    rest = rest.slice(cut).trimStart();
  }
  if (rest) chunks.push(rest);
  return chunks;
}

// --- twilio ---
function twilioVerify(params, header) {
  // signature = Base64(HMAC-SHA1(auth_token, PUBLIC_URL + sorted(key+value)))
  let data = PUBLIC_URL;
  for (const k of Object.keys(params).sort()) data += k + params[k];
  const expected = crypto.createHmac('sha1', TWILIO_AUTH_TOKEN).update(data).digest('base64');
  const got = Buffer.from(String(header || ''), 'utf8');
  const want = Buffer.from(expected, 'utf8');
  return got.length === want.length && crypto.timingSafeEqual(got, want);
}

async function twilioSend(toDigits, body) {
  // Some accounts (2026 trial/tryout) require a ContentSid on every WhatsApp
  // send. With TWILIO_CONTENT_SID set to a passthrough template ("{{1}}"),
  // the whole reply travels as the template variable; otherwise freeform Body.
  const params = { From: TWILIO_WHATSAPP_FROM, To: `whatsapp:+${toDigits}` };
  if (process.env.TWILIO_CONTENT_SID) {
    params.ContentSid = process.env.TWILIO_CONTENT_SID;
    params.ContentVariables = JSON.stringify({ 1: body });
  } else {
    params.Body = body;
  }
  const res = await fetch(
    `https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Messages.json`,
    {
      method: 'POST',
      headers: {
        Authorization: 'Basic ' + Buffer.from(`${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}`).toString('base64'),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams(params),
    },
  );
  if (!res.ok) log(`twilio API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res.ok;
}

// --- telegram ---
function telegramApiOnce(method, payload, timeoutMs) {
  // Use node:https instead of fetch/undici so socket destruction is a genuine
  // hard deadline even during DNS/connect/TLS. `agent: false` prevents a dead
  // keep-alive socket surviving a laptop sleep or Wi-Fi handoff.
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload);
    const started = Date.now();
    const req = https.request({
      hostname: 'api.telegram.org', family: 4, agent: false,
      path: `/bot${TELEGRAM_BOT_TOKEN}/${method}`, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, (res) => {
      let raw = '';
      res.setEncoding('utf8');
      res.on('data', (d) => { raw += d; if (raw.length > 2_000_000) req.destroy(new Error('Telegram response too large')); });
      res.on('end', () => {
        let j = {};
        try { j = JSON.parse(raw); } catch { return reject(new Error(`${method} returned invalid JSON (${res.statusCode})`)); }
        const elapsedMs = Date.now() - started;
        logEvent('telegram_api', { method, elapsed_ms: elapsedMs, ok: Boolean(j.ok), status: res.statusCode });
        if (!j.ok) log(`telegram ${method} ${res.statusCode}: ${JSON.stringify(j).slice(0, 200)}`);
        resolve(j);
      });
    });
    const timer = setTimeout(() => req.destroy(
      new Error(`${method} hard timeout after ${timeoutMs / 1000}s`)), timeoutMs);
    req.on('close', () => clearTimeout(timer));
    req.on('error', reject);
    req.end(body);
  });
}

async function telegramApi(method, payload, timeoutMs = 15_000, retries = 1) {
  let last;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try { return await telegramApiOnce(method, payload, timeoutMs); }
    catch (e) {
      last = e;
      logEvent('telegram_api_error', { method, attempt: attempt + 1, error: e.message });
      if (attempt < retries) await new Promise((r) => setTimeout(r, 500));
    }
  }
  throw last;
}

async function telegramSend(chatId, text) {
  const result = await telegramApi(
    'sendMessage', { chat_id: Number(chatId), text }, 12_000, 1);
  if (!result.ok) throw new Error(`Telegram sendMessage rejected: ${result.description || 'unknown error'}`);
  return true;
}

const MIME = { '.html': 'text/html', '.pdf': 'application/pdf', '.svg': 'image/svg+xml', '.png': 'image/png', '.csv': 'text/csv', '.md': 'text/markdown' };

async function telegramSendDocument(chatId, filePath, caption) {
  const fd = new FormData();
  fd.append('chat_id', String(Number(chatId)));
  if (caption) fd.append('caption', caption.slice(0, 1000));
  const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
  fd.append('document', new Blob([fs.readFileSync(filePath)], { type }), path.basename(filePath));
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(new Error('sendDocument hard timeout after 120s')), 120_000);
  const started = Date.now();
  try {
    const res = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument`, {
      method: 'POST', body: fd, signal: ac.signal,
    });
    const j = await res.json().catch(() => ({}));
    logEvent('telegram_api', { method: 'sendDocument', elapsed_ms: Date.now() - started,
      ok: Boolean(j.ok), status: res.status });
    if (!j.ok) log(`telegram sendDocument ${res.status}: ${JSON.stringify(j).slice(0, 200)}`);
    return j.ok;
  } finally {
    clearTimeout(timer);
  }
}

// Pull "FILE: /abs/path" directives out of a reply. Only files inside the desk
// repo may leave the laptop — and never anything under the bridge dir (.env).
function extractFileDirectives(reply) {
  const files = [], lines = [];
  for (const line of String(reply).split('\n')) {
    const m = line.match(/^\s*FILE:\s*(\/\S.*?)\s*$/);
    if (!m) { lines.push(line); continue; }
    const p = path.resolve(m[1]);
    const inDesk = p.startsWith(DESK_DIR + path.sep);
    const inBridge = p.startsWith(BRIDGE_DIR + path.sep);
    const hidden = p.split(path.sep).some((seg) => seg.startsWith('.'));
    let ok = inDesk && !inBridge && !hidden;
    if (ok) {
      try { const st = fs.statSync(p); ok = st.isFile() && st.size < 45 * 1024 * 1024; }
      catch { ok = false; }
    }
    if (ok) files.push(p);
    else { log(`blocked FILE directive: ${m[1]}`); lines.push(`(file not sendable: ${path.basename(m[1])})`); }
  }
  return { text: lines.join('\n').trim(), files };
}

async function telegramPollLoop() {
  const startedSec = Math.floor(Date.now() / 1000) - 60; // skip pre-start backlog
  log('telegram long-polling mode — near-instant delivery, no inbound port, no tunnel');
  let offset = 0, failures = 0;
  for (;;) {
    try {
      // Short polls plus a 5s hard-deadline margin recover quickly after sleep,
      // Wi-Fi handoff, or a silently dropped route.
      const j = await telegramApi('getUpdates', {
        timeout: 20, offset, allowed_updates: ['message'],
      }, 25_000, 0);
      failures = 0;
      for (const u of j.result || []) {
        offset = Math.max(offset, u.update_id + 1);
        const m = u.message;
        if (!m?.text || !m.from) continue;
        if (m.date < startedSec) continue; // stale backlog — acknowledged, not processed
        enqueue(`tg${m.message_id}-${m.chat.id}`, String(m.from.id), m.text.trim(), String(m.chat.id), m.date * 1000);
      }
    } catch (e) {
      failures++;
      log('telegram poll error:', e.message);
      await new Promise((r) => setTimeout(r, Math.min(1000 * failures, 10_000)));
    }
  }
}

// --- meta ---
function metaVerify(rawBody, header) {
  if (!header?.startsWith('sha256=')) return false;
  const expected = crypto.createHmac('sha256', APP_SECRET).update(rawBody).digest('hex');
  const got = header.slice(7);
  return got.length === expected.length &&
    crypto.timingSafeEqual(Buffer.from(got, 'hex'), Buffer.from(expected, 'hex'));
}

async function metaGraphPost(body) {
  const res = await fetch(`https://graph.facebook.com/${GRAPH_VERSION}/${PHONE_NUMBER_ID}/messages`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) log(`graph API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res.ok;
}

// --- discord ---
async function discordApi(route, options = {}) {
  const res = await fetch(`https://discord.com/api/v10${route}`, {
    ...options,
    headers: {
      Authorization: `Bot ${DISCORD_BOT_TOKEN}`,
      'User-Agent': 'AITraderToolboxBridge/3.0',
      ...(options.headers || {}),
    },
  });
  if (!res.ok) log(`discord API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res;
}

async function discordSend(channelId, body) {
  const res = await discordApi(`/channels/${channelId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: body, allowed_mentions: { parse: [] } }),
  });
  return res.ok;
}

async function discordSendDocument(channelId, filePath, caption) {
  const form = new FormData();
  form.append('payload_json', JSON.stringify({ content: caption || '', allowed_mentions: { parse: [] } }));
  const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
  form.append('files[0]', new Blob([fs.readFileSync(filePath)], { type }), path.basename(filePath));
  const res = await discordApi(`/channels/${channelId}/messages`, { method: 'POST', body: form });
  return res.ok;
}

async function discordPollLoop() {
  log(`discord polling mode — channel ${DISCORD_CHANNEL_ID}, every ${POLL_MS / 1000}s`);
  let after = state.discordLastMessageId || null;
  let initializing = !after;
  let failures = 0;
  for (;;) {
    try {
      const query = after ? `?after=${encodeURIComponent(after)}&limit=100` : '?limit=1';
      const res = await discordApi(`/channels/${DISCORD_CHANNEL_ID}/messages${query}`);
      if (!res.ok) throw new Error(`Discord poll returned ${res.status}`);
      const messages = await res.json();
      for (const m of messages.reverse()) {
        // On first install, establish a watermark without replaying the latest
        // historical command into a potentially resumable trading session.
        if (!initializing && !m.author?.bot && m.content?.trim()) {
          enqueue(`discord-${m.id}`, String(m.author.id), m.content.trim(), String(m.channel_id), Date.parse(m.timestamp));
        }
        if (!after || BigInt(m.id) > BigInt(after)) after = m.id;
      }
      initializing = false;
      if (after && after !== state.discordLastMessageId) {
        state.discordLastMessageId = after;
        saveState(state);
      }
      failures = 0;
    } catch (e) {
      failures++;
      log('discord poll error:', e.message);
    }
    await new Promise((r) => setTimeout(r, Math.min(POLL_MS * (failures + 1), 60_000)));
  }
}

// Every transport implements the same small contract. The desk/message flow
// below never needs to know which app delivered a message.
const messengers = {
  telegram: {
    maxTextChars: 3900,
    send: telegramSend,
    sendFile: telegramSendDocument,
    typing: (to) => telegramApi('sendChatAction', { chat_id: Number(to), action: 'typing' }).catch(() => {}),
    start: telegramPollLoop,
    mode: 'long-poll',
  },
  discord: {
    maxTextChars: 1900,
    send: discordSend,
    sendFile: discordSendDocument,
    typing: (to) => discordApi(`/channels/${to}/typing`, { method: 'POST' }).then((r) => r.ok),
    start: discordPollLoop,
    mode: 'poll',
  },
  twilio: {
    maxTextChars: 1500,
    send: twilioSend,
    sendFile: null,
    typing: null,
    start: TWILIO_POLLING ? pollLoop : null,
    mode: TWILIO_POLLING ? 'poll' : 'webhook',
  },
  meta: {
    maxTextChars: 3900,
    send: (to, body) => metaGraphPost({ messaging_product: 'whatsapp', to, type: 'text', text: { body } }),
    sendFile: null,
    typing: null,
    start: null,
    mode: 'webhook',
  },
};
const messenger = messengers[PROVIDER];

async function sendText(to, text) {
  for (const body of chunkText(text, messenger.maxTextChars)) await messenger.send(to, body);
}

async function sendStatus(to, kind, text) {
  try {
    await sendText(to, text);
    logEvent('status_sent', { kind, provider: PROVIDER });
    return true;
  } catch (e) {
    log(`status send failed (${kind}):`, e.message);
    logEvent('status_send_error', { kind, provider: PROVIDER, error: e.message });
    return false;
  }
}

// mark inbound message read + typing indicator (meta only; twilio has no equivalent)
function markReadAndTyping(messageId) {
  if (PROVIDER !== 'meta') return Promise.resolve(true);
  return metaGraphPost({
    messaging_product: 'whatsapp',
    status: 'read',
    message_id: messageId,
    typing_indicator: { type: 'text' },
  });
}

// -------------------------------------------------------- message flow -----
const seenIds = new Set(); // webhook deliveries can retry — dedup by message id
let queue = Promise.resolve(); // never run two claude sessions concurrently
let activeRun = null; // { prompt, startedMs } while a claude run is in flight
let queueDepth = 0;   // messages waiting behind it

async function handleInbound(replyTo, text, sentAtMs = null) {
  queueDepth = Math.max(0, queueDepth - 1); // this message just left the queue
  const cmd = text.toLowerCase();
  if (cmd === '/new') {
    state.sessionId = null; state.claudeSessionId = null; state.codexSessionId = null;
    state.lastAgent = null; state.recentHistory = []; saveState(state);
    return sendText(replyTo, 'Fresh sessions started for Codex and Claude. Context cleared.');
  }
  if (cmd === '/agent' || cmd.startsWith('/agent ')) {
    const want = cmd.slice(6).trim();
    if (!want) {
      return sendText(replyTo, `Agent: ${(state.agentPreference || 'auto').toUpperCase()}\nAUTO order: ${AGENT_PRIORITY.map(a => agentLabel(a, a === 'codex' ? CODEX_MODEL : CLAUDE_MODEL)).join(' → ')}\nSwitch: /agent auto | codex | claude`);
    }
    if (!['auto', 'codex', 'claude'].includes(want)) {
      return sendText(replyTo, `Unknown agent "${want}". Use /agent auto | codex | claude`);
    }
    state.agentPreference = want; saveState(state);
    logEvent('agent_preference', { preference: want });
    const detail = want === 'auto' ? `AUTO order: ${AGENT_PRIORITY.map(a => agentLabel(a, a === 'codex' ? CODEX_MODEL : CLAUDE_MODEL)).join(' → ')}`
      : `${want} only; automatic fallback disabled`;
    return sendText(replyTo, `Default agent set: ${want.toUpperCase()}\n${detail}\nApplies to the next message.`);
  }
  if (cmd === '/status' || cmd === '/start') {
    const up = Math.round(process.uptime() / 60);
    const sessions = `Codex ${state.codexSessionId ? state.codexSessionId.slice(0, 8) : 'fresh'} · Claude ${state.claudeSessionId ? state.claudeSessionId.slice(0, 8) : 'fresh'}`;
    const last = state.lastAgent ? agentLabel(state.lastAgent, state.lastAgent === 'codex' ? CODEX_MODEL : CLAUDE_MODEL) : 'none';
    return sendText(replyTo, `Bridge up ${up}m (${PROVIDER})\nAgent: ${(state.agentPreference || 'auto').toUpperCase()}${state.lastAgent ? ` (last: ${last})` : ''}\nMode: ${currentMode()}\nDesk: ${DESK_DIR}\nSessions: ${sessions}\nCommands: /new /status /agent /mode /help`);
  }
  if (cmd === '/mode' || cmd.startsWith('/mode ')) {
    const want = cmd.slice(5).trim();
    if (!want) {
      return sendText(replyTo, `Current mode: ${currentMode().toUpperCase()}\n${MODES[currentMode()]}\n\nSwitch with:\n/mode full — ${MODES.full}\n/mode semi — ${MODES.semi}\n/mode manual — ${MODES.manual}`);
    }
    if (!(want in MODES)) return sendText(replyTo, `Unknown mode "${want}". Use: /mode full | semi | manual`);
    setMode(want);
    logEvent('mode_change', { mode: want });
    return sendText(replyTo, `Mode set: ${want.toUpperCase()}\n${MODES[want]}\n\nApplies from the next message and the next scheduled run.${want === 'full' ? '\n\n⚠️ Full-auto executes only in the configured execution account without per-order confirmation. Kill switch: /mode manual' : ''}`);
  }
  if (cmd === '/help') {
    return sendText(replyTo, `Text anything — it runs on the trading desk through ${agentLabel('codex', CODEX_MODEL)} or ${agentLabel('claude', CLAUDE_MODEL)}.\n\n/agent auto|codex|claude — choose the default agent\n/new — fresh sessions\n/status — bridge health\n/mode — view or set trading mode (full / semi / manual)\n\nAUTO follows ${AGENT_PRIORITY.map(a => agentLabel(a, a === 'codex' ? CODEX_MODEL : CLAUDE_MODEL)).join(' → ')} and falls back only when an agent is unavailable. If a limit hits mid-run, the bridge switches immediately and tells you whether the next agent is continuing context or restarting clean.`);
  }

  const inboundLagS = sentAtMs ? Math.max(0, Math.round((Date.now() - sentAtMs) / 1000)) : null;
  log(`prompt${inboundLagS !== null ? ` (lag ${inboundLagS}s)` : ''}: ${text.slice(0, 120)}`);
  logEvent('inbound', { prompt: text.slice(0, 120), inbound_lag_s: inboundLagS });
  // deterministic status ladder, bridge-sent (never depends on the agent):
  // receipt immediately → "agent running" when the process is actually up →
  // trouble (rate limit / fetch failure) the moment it appears → elapsed
  // pings → result or error
  const looksLong = /report|scan|sweep|analy|research|review|deep|audit|run/i.test(text);
  const startMs = Date.now();
  activeRun = { prompt: text, startedMs: startMs, replyTo };
  const timers = [];
  const rotated = rotateSessionIfNeeded();
  if (rotated) {
    log(`session rotated (${rotated})`);
    logEvent('session_rotate', { reason: rotated });
  }
  // Receipt is ordered before agent startup. Previously this was fire-and-forget,
  // which let it race later messages and silently hid delivery failures.
  await sendStatus(replyTo, 'received', rotated
    ? `📥 Command received — processing… (fresh session: previous chat context ${rotated === 'idle' ? 'went stale' : 'grew too large'} and was retired)`
    : '📥 Command received — processing…');
  timers.push(setTimeout(function ping() {
    const mins = Math.round((Date.now() - startMs) / 60_000);
    sendStatus(replyTo, 'progress', `⏳ Still working — ${mins}m elapsed…`);
    timers.push(setTimeout(ping, 300_000)); // then every 5 minutes
  }, 120_000)); // first ping at 2 minutes
  // Keep transient typing indicators alive for transports that support them.
  if (messenger.typing) {
    const typing = () => Promise.resolve(messenger.typing(replyTo)).catch(() => {});
    typing();
    const t = setInterval(typing, 4500);
    timers.push(t);
  }
  let agentStartS = null;
  let agentStartedTimer = null;
  let agentStartedDetail = null;
  const flushAgentStarted = () => {
    if (!agentStartedTimer || !agentStartedDetail) return;
    clearTimeout(agentStartedTimer);
    agentStartedTimer = null;
    const current = agentStartedDetail?.agent ? agentLabel(agentStartedDetail.agent, agentStartedDetail.model) : agentLabel(agent, model);
    sendStatus(replyTo, 'agent_started', looksLong
      ? `🤖 ${current} running — full reports can take a few minutes (up to ~20). The result lands here when done.`
      : `🤖 ${current} running — this might take a few minutes…`);
    agentStartedDetail = null;
  };
  const { ok, text: reply, costUsd, tokens, agent = 'unknown', model = null } = await runPreferredAgent(text, (kind, detail) => {
    if (kind === 'started') {
      agentStartS = Math.round((Date.now() - startMs) / 1000);
      agentStartedDetail = detail || { agent, model };
      agentStartedTimer = setTimeout(flushAgentStarted, 1000);
      logEvent('agent_started', { after_s: agentStartS });
    } else if (kind === 'switch') {
      if (agentStartedTimer) {
        clearTimeout(agentStartedTimer);
        agentStartedTimer = null;
        agentStartedDetail = null;
      }
      const from = detail?.from ? agentLabel(detail.from.name, detail.from.model) : 'unknown';
      const to = detail?.to ? agentLabel(detail.to.name, detail.to.model) : null;
      const mode = detail?.restart ? 'restarting clean' : 'continuing the current thread';
      sendStatus(replyTo, 'agent_fallback', `🔄 Switching ${from}${to ? ` -> ${to}` : ''}; ${mode}.\n${detail?.reason || 'agent changed.'}`);
    } else if (kind === 'trouble') {
      sendStatus(replyTo, 'trouble', `⚠️ Hit an issue mid-run — the agent is retrying / working around it:\n${detail}`);
      logEvent('run_trouble', { detail });
    }
  });
  for (const t of timers) { clearTimeout(t); clearInterval(t); }
  activeRun = null;
  const runS = Math.round((Date.now() - startMs) / 1000);
  if (ok) {
    state.lastAgent = agent;
    state.recentHistory = [...(Array.isArray(state.recentHistory) ? state.recentHistory : []),
      { role: 'user', text: text.slice(0, 2000) }, { role: 'assistant', text: String(reply).slice(0, 3000) }].slice(-12);
    saveState(state);
  }
  logEvent('agent_run', {
    agent, ok, duration_s: runS, reply_chars: String(reply).length,
    cost_usd: costUsd, tokens, session_kb: sessionTranscriptKB(),
  });
  if (!ok) {
    await sendText(replyTo, `⚠️ Error — the run failed:\n${String(reply).trim().slice(0, 3000) || '(no error detail)'}`);
    log('replied with error');
    logEvent('reply_error', { detail: String(reply).trim().slice(0, 500) });
    logTiming({ prompt: text.slice(0, 80), phone_to_bridge_s: inboundLagS, agent_start_s: agentStartS, run_s: runS, reply_sent_s: Math.round((Date.now() - startMs) / 1000), ok: false, files: 0 });
    return;
  }
  const { text: replyText, files } = extractFileDirectives(reply);
  if (replyText) await sendText(replyTo, replyText);
  for (const f of files) {
    if (messenger.sendFile) {
      await messenger.sendFile(replyTo, f, path.basename(f));
      log(`sent file: ${f}`);
      logEvent('file_sent', { file: f });
    } else {
      await sendText(replyTo, `(report ready on the laptop: ${f} — ${PROVIDER} file delivery is not enabled yet)`);
    }
  }
  log('replied');
  logTiming({ prompt: text.slice(0, 80), phone_to_bridge_s: inboundLagS, agent_start_s: agentStartS, run_s: runS, reply_sent_s: Math.round((Date.now() - startMs) / 1000), ok: true, files: files.length });
}

function enqueue(id, from, text, replyTo = from, sentAtMs = null) {
  if (seenIds.has(id)) return;
  seenIds.add(id);
  if (seenIds.size > 500) seenIds.delete(seenIds.values().next().value);

  // HARD GATE: only the owner drives the desk
  if (from !== ALLOWED_SENDER) {
    log(`ignored message from non-allowlisted sender ${from}`);
    return;
  }
  if (/^(join|stop)\b/i.test(text)) return; // twilio sandbox control words, not prompts
  // runs are serialized — if one is active, say so NOW instead of leaving the
  // message in a silent queue (seen 2026-07-11: a 12:49 message waited 47 min
  // behind a long run with zero acknowledgment)
  if (activeRun) {
    const mins = Math.round((Date.now() - activeRun.startedMs) / 60_000);
    queueDepth++;
    logEvent('queued', { prompt: text.slice(0, 80), behind_mins: mins, position: queueDepth });
    sendText(replyTo, `📥 Received — queued behind the current run ("${activeRun.prompt.slice(0, 60)}", running ${mins}m${queueDepth > 1 ? `; position ${queueDepth}` : ''}). It starts as soon as that finishes.`).catch(() => {});
  }
  queue = queue.then(() => handleInbound(replyTo, text, sentAtMs)).catch((e) => {
    log('handler error:', e);
    logEvent('handler_error', { error: String(e?.message || e) });
    sendText(replyTo, `⚠️ Bridge error: ${e?.message || e}`).catch(() => {});
  });
}

// ---------------------------------------------------- twilio polling mode --
// Inbound messages land in Twilio's message log; pull them over outbound
// HTTPS instead of exposing a public webhook. Only messages created after
// process start are processed (restart-safe, no replay).
async function pollOnce(sinceMs) {
  const url = `https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Messages.json` +
    `?PageSize=20&To=${encodeURIComponent(TWILIO_WHATSAPP_FROM)}`;
  const res = await fetch(url, {
    headers: {
      Authorization: 'Basic ' + Buffer.from(`${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}`).toString('base64'),
    },
  });
  if (!res.ok) {
    log(`twilio poll ${res.status}: ${(await res.text()).slice(0, 200)}`);
    return;
  }
  const { messages = [] } = await res.json();
  // newest first — reverse so a burst is handled in send order
  for (const m of messages.reverse()) {
    if (m.direction !== 'inbound' || !m.body) continue;
    const ts = Date.parse(m.date_created);
    if (ts < sinceMs) continue;
    // persisted watermark: a restart (or a skewed clock) must never replay an
    // already-handled message — a stale "yes" replayed into a resumed session
    // could confirm a pending order ticket.
    if (state.lastPollTs && ts <= state.lastPollTs) continue;
    enqueue(m.sid, String(m.from || '').replace(/\D/g, ''), m.body.trim());
    if (!state.lastPollTs || ts > state.lastPollTs) { state.lastPollTs = ts; saveState(state); }
  }
}

async function pollLoop() {
  const startedAt = Date.now() - 60_000; // small grace window for clock skew
  log(`twilio polling mode — checking every ${POLL_MS / 1000}s (no inbound port, no tunnel)`);
  let failures = 0;
  for (;;) {
    try { await pollOnce(startedAt); failures = 0; }
    catch (e) { failures++; log('poll error:', e.message); }
    // back off on repeated failures (network down, laptop waking from sleep)
    await new Promise((r) => setTimeout(r, Math.min(POLL_MS * (failures + 1), 60_000)));
  }
}

// --------------------------------------------------------------- server ----
function handleTwilioPost(raw, req, res) {
  const params = Object.fromEntries(new URLSearchParams(raw.toString('utf8')));
  if (!twilioVerify(params, req.headers['x-twilio-signature'])) {
    log('rejected POST: bad twilio signature');
    res.writeHead(401);
    return res.end();
  }
  // ack with empty TwiML — the real reply goes out via the REST API
  res.writeHead(200, { 'Content-Type': 'text/xml' });
  res.end('<?xml version="1.0" encoding="UTF-8"?><Response></Response>');

  const from = String(params.From || '').replace(/\D/g, ''); // "whatsapp:+1415..." -> digits
  const text = String(params.Body || '').trim();
  if (!params.MessageSid || !text) return;
  enqueue(params.MessageSid, from, text);
}

function handleMetaPost(raw, req, res) {
  if (!metaVerify(raw, req.headers['x-hub-signature-256'])) {
    log('rejected POST: bad signature');
    res.writeHead(401);
    return res.end();
  }
  res.writeHead(200); res.end(); // ack fast — Meta retries slow webhooks

  let payload;
  try { payload = JSON.parse(raw.toString('utf8')); } catch { return; }
  for (const entry of payload.entry || []) {
    for (const change of entry.changes || []) {
      for (const msg of change.value?.messages || []) {
        if (msg.type !== 'text' || !msg.text?.body) continue;
        markReadAndTyping(msg.id).catch(() => {});
        enqueue(msg.id, msg.from, msg.text.body.trim());
      }
    }
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  if (url.pathname !== '/webhook') { res.writeHead(404); return res.end(); }

  // Meta webhook verification handshake (twilio never sends GET — 403 is fine)
  if (req.method === 'GET') {
    if (PROVIDER === 'meta' &&
        url.searchParams.get('hub.mode') === 'subscribe' &&
        url.searchParams.get('hub.verify_token') === VERIFY_TOKEN) {
      res.writeHead(200);
      return res.end(url.searchParams.get('hub.challenge'));
    }
    res.writeHead(403);
    return res.end();
  }

  if (req.method !== 'POST') { res.writeHead(405); return res.end(); }

  const bufs = [];
  req.on('data', (d) => bufs.push(d));
  req.on('end', () => {
    const raw = Buffer.concat(bufs);
    if (PROVIDER === 'twilio') handleTwilioPost(raw, req, res);
    else handleMetaPost(raw, req, res);
  });
});

// a service restart (launchctl unload) SIGTERMs the bridge and kills any
// in-flight claude run with it — without this, the phone sees "Agent
// running…" and then silence forever (bit the META report on 2026-07-11)
process.on('SIGTERM', () => {
  const dying = activeRun;
  logEvent('shutdown', dying ? { interrupted: dying.prompt.slice(0, 80) } : {});
  if (!dying) process.exit(0);
  const mins = Math.round((Date.now() - dying.startedMs) / 60_000);
  Promise.race([
    sendText(dying.replyTo, `⚠️ The bridge was restarted mid-run — "${dying.prompt.slice(0, 60)}" (${mins}m in) was interrupted and won't finish. Please resend it.`),
    new Promise((r) => setTimeout(r, 4000)),
  ]).finally(() => process.exit(0));
});

logEvent('startup', { provider: PROVIDER, mode: messenger.mode });
if (messenger.start) {
  messenger.start();
} else {
  server.listen(PORT, '127.0.0.1', () => {
    log(`bridge listening on http://127.0.0.1:${PORT}/webhook — provider: ${PROVIDER}`);
  });
}
