// Read-only adapter for the installed 0.2.1-rc.2 runtime shape. No answerer,
// claim, RPC, task control, or mutation of host collections is installed here.
// See docs/verification/issue-41 for source anchors and coverage limits.
const LIMIT = 16384;
const validId = value => typeof value === 'string' && value.length > 0 && value.length <= 256;
const callIdOf = data => data.callId ?? data.message?.toolCallId
  ?? data.message?.callId ?? data.message?.source?.callId;

export function currentState(ctx) {
  const caches = new WeakMap();
  function fold(agent) {
    const session = agent.session;
    if (!Number.isSafeInteger(session.seq) || typeof session.eventAt !== 'function') return undefined;
    const boundary = ctx.agents.turnBoundaryOf?.(session)
      ?? ctx.sessionProjections.stateOf(session, 'turnBoundary');
    if (!boundary || !Number.isSafeInteger(boundary.lastTurn)) throw new Error('turn boundary');
    let cache = caches.get(session);
    if (!cache || cache.cursor > session.seq || session.seq - cache.cursor > LIMIT) {
      cache = { cursor: session.inheritedEventCount ?? 0, turn: 0, tools: new Map(),
        questionCalls: new Set(), intervals: [], open: false, start: 0 };
      // Closed history is only needed for child attribution. Cap work per tick.
      if (session.seq - cache.cursor > LIMIT) {
        cache.cursor = boundary.openTurnStartSeq ?? session.seq;
      }
      caches.set(session, cache);
    }
    if (session.seq - cache.cursor > LIMIT) throw new Error('event capacity');
    for (; cache.cursor < session.seq; cache.cursor++) {
      const event = session.eventAt(cache.cursor);
      if (!event || event.seq !== cache.cursor) throw new Error('event gap');
      const data = event.data;
      if (event.type === 'turn/start') {
        cache.turn = data.turn;
        cache.tools.clear();
        cache.questionCalls.clear();
        cache.open = true;
        cache.start = event.time;
        cache.intervals.push({ turn: data.turn, start: event.time, end: Infinity });
        if (cache.intervals.length > 4096) cache.intervals.shift();
      } else if (event.type === 'turn/end') {
        cache.open = false;
        cache.tools.clear();
        if (cache.intervals.length) cache.intervals.at(-1).end = event.time;
      } else if (cache.open && (!data.turn || data.turn === cache.turn)) {
        if (event.type === 'tool/call' || event.type === 'tool/ptc-dispatch-start') {
          const id = data.subCallId ?? data.callId;
          if (!validId(id) || cache.tools.size >= 4096) throw new Error('call capacity');
          cache.tools.set(id, { name: data.name, parent: data.parentCallId });
          if (data.name === 'ask_user_question') cache.questionCalls.add(id);
        } else if (event.type === 'tool/result' || event.type === 'tool/ptc-dispatch') {
          cache.tools.delete(data.subCallId ?? callIdOf(data));
        }
      }
    }
    if (cache.turn !== boundary.lastTurn || cache.open !== (boundary.openTurnStartSeq != null)) {
      // An idle boundary can legitimately precede the first retained event.
      if (boundary.openTurnStartSeq != null) throw new Error('boundary mismatch');
      cache.turn = boundary.lastTurn;
      cache.open = false;
    }
    return cache;
  }

  function read(agent, live) {
    const cache = fold(agent);
    if (!cache) return undefined; // Older host/test sources retain observed-only fallback.
    let root = agent;
    let childStart = cache.start;
    let rootTurn = cache.turn;
    let ownershipKnown = true;
    const visited = new Set([agent]);
    while (true) {
      const parent = live.find(candidate => ctx.agents.isOwnedBy(root.id, candidate));
      if (!parent) break;
      if (visited.has(parent)) throw new Error('ownership cycle');
      visited.add(parent);
      const parentCache = fold(parent);
      // Do not attach an old child's work to its parent's latest request.
      const interval = parentCache?.intervals.filter(item =>
        Number.isFinite(childStart) && item.start < childStart && childStart <= item.end).at(-1);
      if (!interval) ownershipKnown = false;
      rootTurn = interval?.turn ?? 0;
      childStart = interval?.start;
      root = parent;
    }
    const questions = new Set();
    const approvals = new Set();
    const blocked = new Set();
    let waitsKnown = true;
    const gateway = ctx.typertGateway;
    const browser = ctx.connection?.browserPeer;
    if (!(gateway?.pendingRemoteEvents instanceof Map) || !browser) waitsKnown = !cache.open;
    else {
      if (gateway.pendingRemoteEvents.size > 4096) throw new Error('wait capacity');
      for (const pending of gateway.pendingRemoteEvents.values()) {
        if (!cache.open) continue;
        const frame = pending.frame;
        if (frame?.agentId !== agent.id || !['approval/request', 'user-questions/request'].includes(frame.event)) continue;
        if (pending.source?.context?.subject !== agent) { waitsKnown = false; continue; }
        const request = pending.source.request;
        const call = request.callId ?? request.wait?.callId;
        const deliveries = [...pending.deliveries];
        const human = deliveries.some(client => client.peer === browser && client.answers);
        const machine = deliveries.some(client => client.peer !== browser && client.answers);
        if (!human || machine || !validId(call) || !validId(pending.id)) {
          waitsKnown = false;
          continue;
        }
        (frame.event === 'approval/request' ? approvals : questions).add(pending.id);
        blocked.add(call);
      }
    }
    // Continued timed questions are answerable even after foreground execution resumes.
    const projection = ctx.sessionProjections.stateOf(agent.session, 'userQuestions');
    if (projection?.questions?.active) {
      if (projection.questions.active.length > 4096) throw new Error('question capacity');
      for (const question of projection.questions.active) {
        if (!validId(question.callId)) throw new Error('question identity');
        if (question.state === 'continued') {
          if (cache.questionCalls.has(question.callId)) questions.add(question.callId);
          else waitsKnown = false; // Do not attach an earlier turn's question to this one.
        }
      }
    }
    const childrenByParent = new Map();
    for (const [id, item] of cache.tools) {
      if (!childrenByParent.has(item.parent)) childrenByParent.set(item.parent, []);
      childrenByParent.get(item.parent).push(id);
    }
    const isBlocked = (id, seen = new Set()) => {
      if (seen.has(id)) throw new Error('call cycle');
      seen.add(id);
      if (blocked.has(id)) return true;
      const children = childrenByParent.get(id) ?? [];
      return children.length > 0 && children.every(child => isBlocked(child, new Set(seen)));
    };
    const work = [...cache.tools.keys()].some(id => !isBlocked(id));
    // A run_code wrapper can run independent code while its nested calls wait.
    // The rc.2 log does not expose that program's suspended/runnable state.
    const nestedOnlyWait = !work && [...cache.tools.keys()].some(id =>
      !blocked.has(id) && childrenByParent.has(id));
    const pending = questions.size + approvals.size > 0;
    const status = cache.open ? (pending && cache.tools.size > 0 && !work ? 'waiting' : 'running')
      : pending ? 'waiting' : 'idle';
    return { id: agent.id, root: root.id, rootTurn, turn: cache.turn, status,
      known: ownershipKnown && waitsKnown && !nestedOnlyWait,
      questions, approvals, tools: new Set(cache.tools.keys()),
      sourceSeq: agent.session.seq };
  }
  return { read };
}
