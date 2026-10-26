// A controlled writer process using the actual plugin, not a real Harness session.
import { EventEmitter } from 'node:events';
import { createInterface } from 'node:readline';
import { apply } from '../src/sukuna_pet/integrations/dsh-bridge/index.js';
const events = new EventEmitter();
const agentEvents = new EventEmitter();
let dispose = [];
let turn = 0;
const session = { id: 'native-controlled-root' };
const agent = { id: session.id, session, status: 'idle', ctx: {
  on(type, fn) { agentEvents.on(type, fn); return () => agentEvents.off(type, fn); },
} };
const ctx = { agents: { list: () => [agent], isOwnedBy: () => false },
  sessionProjections: { stateOf: () => ({ lastTurn: turn, openTurnStartSeq: turn || null }) },
  on(type, fn) { events.on(type, fn); return () => events.off(type, fn); },
  effect(fn) { dispose.push(fn()); } };
apply(ctx);
const send = (type, data) => events.emit('session/event', session, { type, data });
const input = createInterface({ input: process.stdin });
input.on('line', async line => {
  if (line === 'start') send('turn/start', { turn: ++turn });
  if (line === 'load') for (let i = 0; i < 20000; i++) send('step/start', { turn });
  if (line === 'wait') send('tool/call', { turn, callId: 'native-question', name: 'ask_user_question' });
  if (line === 'end') send('turn/end', { turn, reason: { kind: 'completed' } });
  if (line === 'close') {
    for (const stop of dispose) await stop();
    input.close();
    process.exit(0);
  }
});
