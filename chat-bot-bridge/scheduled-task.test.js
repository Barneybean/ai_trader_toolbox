import test from 'node:test';
import assert from 'node:assert/strict';
import { buildScheduledPrompt, scheduledLabel } from './scheduled-task.js';

test('builds decision-grade premarket prompt with active mode', () => {
  const prompt = buildScheduledPrompt('premarket', 'semi', new Date('2026-07-13T12:45:00Z'));
  assert.match(prompt, /PRE-MARKET complete daily report/);
  assert.match(prompt, /SEMI-AUTO/);
  assert.match(prompt, /bilingual HTML report/);
  assert.match(prompt, /MANDATORY SCHEDULED-REPORT BROKER PREFLIGHT/);
});

test('keeps plumbing test cheap and validates kinds', () => {
  assert.equal(buildScheduledPrompt('test', 'manual'), 'This is a scheduled-run plumbing test. Reply with exactly: scheduled-run test ok');
  assert.equal(scheduledLabel('postmarket'), 'Post-market');
  assert.throws(() => buildScheduledPrompt('unknown', 'manual'), /unknown scheduled kind/);
});
