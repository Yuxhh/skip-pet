// File bridge adapted from the architecture of Merzlin/dsh-pet-indesktop
// 34d810b1 (MIT, copyright Merzlin 2026). See LICENSE and docs/verification.
// Export only IDs/enums: never forward event payloads, messages or questions.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export const name = 'sukuna-pet-dsh-bridge';
export const inject = ['agents', 'sessionProjections'];

export function apply(ctx) {
  const directory = process.env.SUKUNA_PET_BRIDGE_DIR || path.join(
    process.env.LOCALAPPDATA || path.join(os.homedir(), '.local', 'share'),
    'sukuna-pet', 'bridge', 'dsh',
  );
  fs.mkdirSync(directory, { recursive: true });
  const file = path.join(directory, `dsh-${process.pid}.jsonl`);
  const snapshotFile = path.join(directory, `dsh-${process.pid}.snapshot.json`);
  const boot = randomUUID();
  let revision = 0;
  let health = 0;
  let records = [];
  let disposed = false;
  const agents = new Map();
  const stops = new Map();
  const idOf = agent => String(agent?.session?.id || agent?.id || '');
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
  function record(event, data = {}) {
    records.push({ schema: 1, boot_id: boot, pid: process.pid, revision: ++revision,
      event, ...data });
    if (records.length > 1024) {
      // Current observed state remains in the next snapshot; never grow unbounded.
      records = [];
    }
  }
  function flush() {
    if (!records.length) return;
    try {
      if (fs.existsSync(file) && fs.statSync(file).size > 1024 * 1024) {
        fs.rmSync(`${file}.1`, { force: true });
        fs.renameSync(file, `${file}.1`);
      }
      fs.appendFileSync(file, records.map(row => JSON.stringify(row)).join('\n') + '\n');
      records = [];
    } catch { records = []; } // The reader detects the sequence gap / stale health.
  }
  function publicState(state) {
    return { agent_id: state.id, root_id: state.root, root_turn: state.rootTurn,
      turn_id: state.turn, status: state.status, known: state.known,
      question_ids: [...state.questions], approval_ids: [...state.approvals] };
  }
  function track(agent) {
    const id = idOf(agent);
    if (!id || agents.has(id)) return agents.get(id);
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
    const stop = agent.ctx.on('agent/status', ({ status }) => {
      if (disposed) return;
      if (status === 'idle') state.status = 'idle';
      else if (state.status === 'idle') { state.status = 'running'; state.known = false; }
      record('agent/state', publicState(state));
    });
    stops.set(id, stop);
    return state;
  }
  function syncAgents() {
    const live = registry.list();
    for (const agent of live) track(agent);
    for (const [id, state] of agents) {
      if (!live.some(agent => idOf(agent) === id)) {
        stops.get(id)?.();
        stops.delete(id);
        agents.delete(id);
        record('agent/removed', publicState(state));
      }
    }
  }
  function snapshot(lifecycle = 'active') {
    try {
      const value = { schema: 1, boot_id: boot, pid: process.pid, revision,
        health_seq: ++health, lifecycle, coverage: 'observed',
        // This baseline reproduces observed state, not an authoritative host snapshot.
        agents: [...agents.values()].map(publicState) };
      const temporary = `${snapshotFile}.${boot}.tmp`;
      fs.writeFileSync(temporary, JSON.stringify(value));
      fs.renameSync(temporary, snapshotFile);
    } catch { /* A failed publication cannot renew reader health. */ }
  }
  ctx.on('agent/created', ({ agent }) => { if (agent) track(agent); });
  ctx.on('session/event', (session, event) => {
    try {
      if (disposed) return;
      const agent = registry.list().find(candidate => idOf(candidate) === String(session.id));
      if (!agent) return;
      const state = track(agent);
      const data = event.data || {};
      const type = event.type;
      if (type === 'turn/start') {
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
        state.tools.add(String(data.callId));
        if (data.name === 'ask_user_question') state.questions.add(String(data.callId));
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
  snapshot();
  const flushTimer = setInterval(() => { if (records.length) { flush(); snapshot(); } }, 80);
  const healthTimer = setInterval(() => { syncAgents(); flush(); snapshot(); }, 1000);
  flushTimer.unref?.();
  healthTimer.unref?.();
  ctx.effect(() => () => {
    disposed = true;
    clearInterval(flushTimer);
    clearInterval(healthTimer);
    for (const stop of stops.values()) stop?.();
    record('bridge/stopped');
    flush();
    snapshot('stopped');
  });
}
