// Host boundary fixture from the installed rc.2 source; the real plugin writes files.
import { EventEmitter } from 'node:events';
import { createInterface } from 'node:readline';
import { apply } from '../src/sukuna_pet/integrations/dsh-bridge/index.js';
const events = new EventEmitter();
let cleanups = [];
const browserPeer = {};
const pendingRemoteEvents = new Map();
const log = [
  { type: 'turn/start', seq: 0, time: 100, data: { turn: 1 } },
  { type: 'tool/call', seq: 1, time: 101, data: { turn: 1, callId: 'question', name: 'ask_user_question', arguments: 'PRIVATE_QUESTION' } },
];
const session = { id: 'root', get seq() { return log.length; },
  inheritedEventCount: 0, eventAt: seq => log[seq] };
const agentEvents = new EventEmitter();
const agent = { id: 'root', session, status: 'running', ctx: {
  on(name, fn) { agentEvents.on(name, fn); return () => agentEvents.off(name, fn); },
} };
const live = [agent];
let activeQuestions = [];
pendingRemoteEvents.set('remote-question', { id: 'remote-question',
  source: { context: { subject: agent }, request: { wait: { callId: 'question' } } },
  frame: { event: 'user-questions/request', agentId: 'root', request: { wait: { callId: 'question' } } },
  deliveries: new Set([{ peer: browserPeer, answers: true }]),
});
const ctx = {
  agents: { list: () => live, isOwnedBy: (id, owner) => id === 'child' && owner === agent },
  sessionProjections: { stateOf: (value, key) => {
    if (key !== 'turnBoundary') return { questions: { active: value === session ? activeQuestions : [] } };
    const rows = value === session ? log : [value.eventAt(0)];
    const start = rows.findLast(event => event.type === 'turn/start');
    const end = rows.findLast(event => event.type === 'turn/end');
    return { lastTurn: start.data.turn,
      openTurnStartSeq: end && end.seq > start.seq ? null : start.seq };
  } },
  typertGateway: { pendingRemoteEvents }, connection: { browserPeer },
  on(name, fn) { events.on(name, fn); return () => events.off(name, fn); },
  effect(fn) { cleanups.push(fn()); },
};
apply(ctx);
console.log('ready');
const input = createInterface({ input: process.stdin });
for await (const command of input) {
  if (command === 'close') {
    for (const cleanup of cleanups) await cleanup();
    input.close();
    break;
  }
  if (command === 'approval') {
    pendingRemoteEvents.clear();
    log.push({ type: 'tool/result', seq: log.length, time: 102,
      data: { turn: 1, message: { toolCallId: 'question' } } });
    log.push({ type: 'tool/call', seq: log.length, time: 103,
      data: { turn: 1, callId: 'shell', name: 'pwsh' } });
    pendingRemoteEvents.set('remote-approval', { id: 'remote-approval',
      source: { context: { subject: agent }, request: { callId: 'shell' } },
      frame: { event: 'approval/request', agentId: 'root' },
      deliveries: new Set([{ peer: browserPeer, answers: true }]),
    });
  }
  if (command === 'child') {
    const childLog = [{ type: 'turn/start', seq: 0, time: 110, data: { turn: 1 } }];
    const child = { id: 'child', status: 'running',
      session: { id: 'child', seq: 1, inheritedEventCount: 0, eventAt: seq => childLog[seq] },
      ctx: agent.ctx };
    live.push(child);
    events.emit('agent/created', { agent: child });
  }
  if (command === 'continued') {
    pendingRemoteEvents.clear();
    activeQuestions = [{ callId: 'question', state: 'continued', questions: ['PRIVATE_QUESTION'] }];
    const data = { turn: 1, message: { toolCallId: 'question',
      content: [{ type: 'text', text: '{"pending":true}' }] } };
    log.push({ type: 'tool/result', seq: log.length, time: 104, data });
    events.emit('session/event', session, log.at(-1));
  }
  if (command === 'answer') {
    pendingRemoteEvents.clear();
    activeQuestions = [];
  }
  if (command === 'reload') {
    for (const cleanup of cleanups) await cleanup();
    events.removeAllListeners();
    cleanups = [];
    apply(ctx);
  }
  if (command === 'nested') {
    pendingRemoteEvents.clear();
    log[1] = { type: 'tool/call', seq: 1, time: 101,
      data: { turn: 1, callId: 'program', name: 'run_code' } };
    log.push({ type: 'tool/ptc-dispatch-start', seq: log.length, time: 102,
      data: { rootCallId: 'program', parentCallId: 'program', subCallId: 'nested-q', name: 'ask_user_question' } });
    pendingRemoteEvents.set('nested-remote', { id: 'nested-remote',
      source: { context: { subject: agent }, request: { wait: { callId: 'nested-q' } } },
      frame: { event: 'user-questions/request', agentId: 'root' },
      deliveries: new Set([{ peer: browserPeer, answers: true }]),
    });
    // Reload from current host facts, including a nested foreground wait.
    for (const cleanup of cleanups) await cleanup();
    events.removeAllListeners();
    cleanups = [];
    apply(ctx);
  }
  if (command === 'machine') {
    for (const pending of pendingRemoteEvents.values()) pending.deliveries.add({ peer: {}, answers: true });
  }
  if (command === 'new-turn') {
    pendingRemoteEvents.clear();
    log.push({ type: 'turn/end', seq: log.length, time: 120,
      data: { turn: 1, reason: { kind: 'completed' } } });
    log.push({ type: 'turn/start', seq: log.length, time: 130, data: { turn: 2 } });
    events.emit('session/event', session, log.at(-1));
  }
  if (command === 'old-end') events.emit('session/event', session,
    { type: 'turn/end', data: { turn: 1, reason: { kind: 'error' } } });
  if (command === 'fail') {
    pendingRemoteEvents.clear();
    activeQuestions = [];
    log.push({ type: 'turn/end', seq: log.length, time: 140,
      data: { turn: 1, reason: { kind: 'error' } } });
    events.emit('session/event', session, log.at(-1));
  }
  await new Promise(resolve => setTimeout(resolve, 1200));
  console.log(`applied ${command}`);
}
