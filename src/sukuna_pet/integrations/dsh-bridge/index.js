// File bridge adapted from the architecture of Merzlin/dsh-pet-indesktop
// 34d810b1 (MIT, copyright Merzlin 2026). See LICENSE and docs/verification.
// Export only IDs/enums: never forward event payloads, messages or questions.
import os from 'node:os';
import path from 'node:path';
import { publisher } from './file-publisher.js';
import { currentState } from './host-state.js';

export const name = 'sukuna-pet-dsh-bridge';
export const inject = ['agents', 'sessionProjections'];

export function apply(ctx) {
  const host = currentState(ctx);
  const directory = process.env.SUKUNA_PET_BRIDGE_DIR || path.join(
    process.env.LOCALAPPDATA || path.join(os.homedir(), '.local', 'share'),
    'sukuna-pet', 'bridge', 'dsh',
  );
  let disposed = false;
  const agents = new Map();
  const stops = new Map();
  let coverageComplete = true;
  const idOf = agent => {
    const id = String(agent?.session?.id || agent?.id || '');
    return id.length <= 256 ? id : '';
  };
  const registry = ctx.agents;
  const boundaryOf = session => {
    try {
      return registry.turnBoundaryOf?.(session)
        ?? ctx.sessionProjections.stateOf(session, 'turnBoundary');
    } catch { return undefined; }
  };
  function ownerOf(agent) {
    const visited = new Set();
    let root = agent;
    while (root && !visited.has(root)) {
      visited.add(root);
      const owner = registry.list().find(candidate => registry.isOwnedBy(root.id, candidate));
      if (!owner) break;
      root = owner;
    }
    return root;
  }
  function publicState(state) {
    return { agent_id: state.id, root_id: state.root, root_turn: state.rootTurn,
      turn_id: state.turn, status: state.status, known: state.known,
      question_ids: [...state.questions], approval_ids: [...state.approvals],
      ...(state.sourceSeq === undefined ? {} : { source_seq: state.sourceSeq }) };
  }
  function refresh(agent, state) {
    try {
      const latest = host.read(agent, registry.list());
      if (!latest) return false;
      const before = JSON.stringify(publicState(state));
      Object.assign(state, latest);
      if (before !== JSON.stringify(publicState(state))) record('agent/state', publicState(state));
      return true;
    } catch {
      state.known = false;
      record('agent/state', publicState(state));
      return true;
    }
  }
  function track(agent) {
    const id = idOf(agent);
    if (!id || agents.size >= 4096 && !agents.has(id)) {
      coverageComplete = false;
      return undefined;
    }
    if (agents.has(id)) return agents.get(id);
    const root = ownerOf(agent);
    const boundary = boundaryOf(agent.session);
    const rootBoundary = boundaryOf(root.session);
    const active = boundary?.openTurnStartSeq != null;
    const possiblyActive = active || agent.status === 'running';
    const state = { id, root: idOf(root), rootTurn: rootBoundary?.lastTurn || 0,
      turn: boundary?.lastTurn || 0, status: possiblyActive ? 'running' : 'idle',
      // Late-loaded running turns may already have waits we did not observe.
      known: Boolean(boundary) && !possiblyActive,
      questions: new Set(), approvals: new Set(), tools: new Set() };
    agents.set(id, state);
    refresh(agent, state);
    const stop = agent.ctx.on('agent/status', ({ status }) => {
      if (disposed) return;
      if (refresh(agent, state)) return;
      if (status === 'idle') state.status = 'idle';
      else if (state.status === 'idle') { state.status = 'running'; state.known = false; }
      record('agent/state', publicState(state));
    });
    stops.set(id, stop);
    return state;
  }
  function syncAgents() {
    const live = registry.list();
    const liveIds = new Set(live.map(idOf));
    coverageComplete = live.length <= 4096 && !liveIds.has('');
    for (const [id, state] of agents) {
      if (!liveIds.has(id)) {
        stops.get(id)?.();
        stops.delete(id);
        agents.delete(id);
        record('agent/removed', publicState(state));
      }
    }
    for (const agent of live) {
      const state = track(agent);
      if (state) refresh(agent, state);
    }
  }
  const transport = publisher(directory, () => {
    if (!coverageComplete) throw new Error('observation capacity');
    return [...agents.values()].map(publicState);
  });
  const record = (event, data = {}) => transport.record(event, data);
  ctx.on('agent/created', ({ agent }) => { if (!disposed && agent) track(agent); });
  ctx.on('session/event', (session, event) => {
    try {
      if (disposed) return;
      const agent = registry.list().find(candidate => idOf(candidate) === String(session.id));
      if (!agent) return;
      const state = track(agent);
      if (!state) return;
      const data = event.data || {};
      const type = event.type;
      if (refresh(agent, state)) {
        if (type === 'turn/end' && data.turn === state.turn && state.status === 'idle') {
          const reason = data.reason?.kind;
          record('turn/end', { ...publicState(state), status: 'idle',
            outcome: reason === 'error' ? 'failed' : reason === 'completed' ? 'completed' : 'interrupted' });
        }
        return;
      }
      if (type === 'turn/start') {
        if (!Number.isSafeInteger(data.turn) || data.turn <= state.turn) return;
        const root = ownerOf(agent);
        state.root = idOf(root);
        state.turn = Number(data.turn) || 0;
        state.rootTurn = root === agent ? state.turn : (boundaryOf(root.session)?.lastTurn || 0);
        state.status = 'running';
        state.known = true;
        state.questions.clear();
        state.approvals.clear();
        state.tools.clear();
      } else if (data.turn && Number(data.turn) !== state.turn) {
        return; // A prior turn cannot change the current turn's state.
      } else if (type === 'turn/end') {
        state.status = 'idle';
        state.questions.clear();
        state.approvals.clear();
        const reason = data.reason?.kind;
        const outcome = reason === 'error' ? 'failed'
          : reason === 'completed' ? 'completed' : 'interrupted';
        record('turn/end', { ...publicState(state), outcome });
      } else if (type === 'tool/call') {
        const callId = String(data.callId || '');
        if (!callId || callId.length > 256 || state.tools.size >= 4096) {
          state.known = false;
          state.tools.clear();
          state.questions.clear();
        } else {
          state.tools.add(callId);
          if (data.name === 'ask_user_question') state.questions.add(callId);
        }
      } else if (type === 'tool/result') {
        const callId = data.callId || data.message?.callId || data.message?.source?.callId;
        state.questions.delete(String(callId));
        state.tools.delete(String(callId));
      } else if (type === 'approval/asked' || type === 'approval/decided') {
        // Keep audit pairing separate from real waits. Never label it human waiting.
        record(type, { ...publicState(state), request_id: String(data.id || '') });
        return;
      } else if (!['step/start', 'step/end', 'assistant/message'].includes(type)) {
        return;
      }
      if (state.status !== 'idle') {
        state.status = state.questions.size && state.tools.size === state.questions.size
          ? 'waiting' : 'running';
      }
      // Reference-style observed question waits; late attach and unobserved
      // nested tools remain gaps to measure, not a claim of full host coverage.
      record('agent/state', publicState(state));
    } catch { /* Observers never throw into the host's task event dispatch. */ }
  });
  syncAgents();
  record('bridge/started');
  transport.request(true);
  const flushTimer = setInterval(() => { if (transport.pending) transport.request(); }, 80);
  const healthTimer = setInterval(() => { syncAgents(); transport.request(true); }, 1000);
  flushTimer.unref?.();
  healthTimer.unref?.();
  ctx.effect(() => () => {
    disposed = true;
    clearInterval(flushTimer);
    clearInterval(healthTimer);
    for (const stop of stops.values()) stop?.();
    return transport.close();
  });
}
