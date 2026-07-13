import test from 'node:test';
import assert from 'node:assert/strict';
import {
  availabilityFailure,
  brokerRequestKind,
  codexAvailabilityError,
  preferredAgentOrder,
  prioritizeBrokerAgent,
} from './agent-routing.js';

test('classifies explicit execution and live-status requests', () => {
  assert.equal(brokerRequestKind('approve 2'), 'action');
  assert.equal(brokerRequestKind('Ok to execute'), 'action');
  assert.equal(brokerRequestKind('execute SOFI'), 'action');
  assert.equal(brokerRequestKind('yes to 2'), 'action');
  assert.equal(brokerRequestKind('cancel the open NKE order'), 'action');
  assert.equal(brokerRequestKind('buy 2 NVDA shares'), 'action');
  assert.equal(brokerRequestKind('check my open orders'), 'status');
  assert.equal(brokerRequestKind('get the live quote for NKE'), 'status');
});

test('puts the MCP-capable broker agent ahead of sticky research routing', () => {
  assert.deepEqual(prioritizeBrokerAgent(['codex', 'claude'], 'claude', 'action'), ['claude', 'codex']);
  assert.deepEqual(prioritizeBrokerAgent(['codex'], 'claude', 'status'), ['claude', 'codex']);
  assert.deepEqual(prioritizeBrokerAgent(['codex', 'claude'], 'claude', null), ['codex', 'claude']);
});

test('agent choice sets the default while retaining available alternatives', () => {
  assert.deepEqual(preferredAgentOrder('codex', ['codex', 'claude']), ['codex', 'claude']);
  assert.deepEqual(preferredAgentOrder('claude', ['codex', 'claude']), ['claude', 'codex']);
  assert.deepEqual(preferredAgentOrder('auto', ['codex', 'claude']), ['codex', 'claude']);
});

test('recognizes synthetic usage-limit replies as fallback eligible', () => {
  assert.equal(availabilityFailure("You've reached your Fable 5 limit. Run /usage-credits to continue."), true);
  assert.equal(availabilityFailure('rate limit reached; try again later'), true);
  assert.equal(availabilityFailure('Report completed normally.'), false);
});

test('does not classify failed command output as Codex unavailability', () => {
  const npmEnoent = {
    type: 'item.completed',
    item: {
      type: 'command_execution', status: 'failed', exit_code: 254,
      stderr: 'npm error code ENOENT: package.json not found',
    },
  };
  assert.equal(codexAvailabilityError(npmEnoent), null);
  assert.match(codexAvailabilityError({ type: 'turn.failed', error: { message: 'rate limit 429' } }), /429/);
});

test('uses recent ticket context for a bare confirmation', () => {
  const history = [{ role: 'assistant', text: 'Ticket 1 is ready. Reply yes to confirm this order.' }];
  assert.equal(brokerRequestKind('yes', history), 'action');
});

test('does not mistake research questions for execution', () => {
  assert.equal(brokerRequestKind('Should I buy NKE after earnings?'), null);
  assert.equal(brokerRequestKind('Explain the order execution methodology'), null);
});
