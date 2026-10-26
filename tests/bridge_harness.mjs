// Exercise the real plugin with a deterministic host-shaped event source.
// No host process, conversations, credentials or production profile are touched.
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const directory = process.argv[2];
process.env.SUKUNA_PET_BRIDGE_DIR = directory;
const { apply } = await import(pathToFileURL(path.resolve('src/sukuna_pet/integrations/dsh-bridge/index.js')));
const events = new EventEmitter();
const agentEvents = new EventEmitter();
const dispose = [];
const session = { id: 'test-session' };
const agent = { id: session.id, session, ctx: {
  on(type, fn) { agentEvents.on(type, fn); return () => agentEvents.off(type, fn); },
} };
let boundary = { openTurnStartSeq: null, lastTurn: 0 };
const ctx = {
  agents: { list: () => [agent], isOwnedBy: () => false },
  sessionProjections: { stateOf: () => boundary },
  on(type, fn) { events.on(type, fn); return () => events.off(type, fn); },
  effect(fn) { dispose.push(fn()); },
};
apply(ctx);
const send = (type, data) => events.emit('session/event', session, { type, data });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const snap = () => JSON.parse(fs.readFileSync(path.join(directory, `dsh-${process.pid}.snapshot.json`)));
boundary = { openTurnStartSeq: 1, lastTurn: 1 };
send('turn/start', { turn: 1 });
send('tool/call', { callId: 'q1', name: 'ask_user_question', arguments: { secret: 'DO_NOT_EXPORT' } });
await pause(110);
assert.equal(snap().agents[0].status, 'waiting');
send('tool/call', { callId: 'job', name: 'pwsh', arguments: 'DO_NOT_EXPORT' });
await pause(100);
assert.equal(snap().agents[0].status, 'running');
send('tool/result', { message: { source: { callId: 'job' } } });
await pause(100);
assert.equal(snap().agents[0].status, 'waiting');
send('tool/result', { message: { source: { callId: 'q1' } } });
await pause(100);
assert.equal(snap().agents[0].status, 'running');
const before = snap().health_seq;
await pause(1100);
assert.ok(snap().health_seq > before);
send('turn/end', { turn: 1, reason: { kind: 'completed' } });
await pause(100);
assert.equal(snap().agents[0].status, 'idle');
for (const fn of dispose) fn();
assert.equal(snap().lifecycle, 'stopped');
const lines = fs.readFileSync(path.join(directory, `dsh-${process.pid}.jsonl`), 'utf8');
assert.ok(!lines.includes('DO_NOT_EXPORT'));
assert.ok(lines.includes('"outcome":"completed"'));
assert.equal(agentEvents.listenerCount('agent/status'), 0);
console.log('Bridge file/health/question/concurrent-tool/end/privacy/disposal checks passed');
