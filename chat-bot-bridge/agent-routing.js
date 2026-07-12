// Pure helpers for agent availability/fallback classification.
// Keep this module side-effect free so the smoke gate can regression-test it.

export const CODEX_UNAVAILABLE_RE = /rate.?limit|usage limit|quota|too many requests|\b429\b|limit reached|try again later|not logged in|authentication|unauthorized|ENOENT|not found/i;

export function codexAvailabilityError(ev) {
  // Never scan the whole event: command_execution events include command text,
  // where harmless phrases such as "not found" caused false phone warnings.
  const eventError = ['error', 'turn.failed'].includes(ev?.type)
    ? [ev.message, ev.error?.message, ev.detail].filter(Boolean).join(' ')
    : '';
  if (eventError && CODEX_UNAVAILABLE_RE.test(eventError)) return eventError;

  const item = ev?.item;
  if (ev?.type === 'item.completed' && item?.type === 'command_execution') {
    const failed = item.status === 'failed' || (Number.isInteger(item.exit_code) && item.exit_code !== 0);
    if (!failed) return null;
    const output = [item.aggregated_output, item.output, item.stderr, item.error?.message]
      .filter(Boolean).join(' ');
    if (output && CODEX_UNAVAILABLE_RE.test(output)) return output;
  }
  return null;
}
