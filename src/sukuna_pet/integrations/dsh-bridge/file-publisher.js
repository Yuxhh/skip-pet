// Transport supplements the reference's 80ms batches and one-backup rotation.
// One asynchronous writer owns a generation; no event callback waits for disk.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { createRequire } from 'node:module';
import { performance } from 'node:perf_hooks';

const MIB = 1024 * 1024;
const slots = new Map();
let lastBootTime = 0;
const hash = value => createHash('sha256').update(value).digest('hex');
const pathId = value => hash(process.platform === 'win32' ? path.resolve(value).toLowerCase() : path.resolve(value));

async function hostVersion() {
  try {
    const require = createRequire(path.join(process.cwd(), 'package.json'));
    return require('@deepseek-ai/dsh/package.json').version;
  } catch {
    try { return JSON.parse(await fs.readFile(path.join(process.argv[2], 'package.json'), 'utf8')).version; }
    catch { return 'unknown'; }
  }
}

export function publisher(directory, observed) {
  const prefix = path.join(directory, `dsh-${process.pid}`);
  const boot = randomUUID();
  const start = String(performance.timeOrigin);
  lastBootTime = Math.max(Date.now(), lastBootTime + 1);
  const identity = { schema_version: 1, owner: '@sukuna-pet/dsh-bridge',
    user_id: pathId(os.homedir()), profile_id: pathId(process.cwd()),
    instance_id: hash(`${pathId(process.cwd())}\0${process.pid}\0${start}`),
    pid: process.pid, process_start_id: start, boot_id: boot, boot_started_at: lastBootTime,
    host_version: 'unknown', plugin_version: '0.2.0',
    capabilities: ['observed-state', 'snapshot-boundary', 'contiguous-events', 'independent-health'] };
  const previous = slots.get(prefix);
  const slot = { boot, tail: previous?.tail || Promise.resolve() };
  slots.set(prefix, slot);
  const owns = () => slots.get(prefix) === slot;
  let revision = 0;
  let health = 0;
  let snapshotSequence = 0;
  let queue = [];
  let queueBytes = 0;
  let inFlightBytes = 0;
  let requested = false;
  let stopping = false;
  let running = false;
  let gapRevision = 0;
  const ready = slot.tail.then(async () => {
    if (!owns()) return;
    await fs.mkdir(directory, { recursive: true, mode: 0o700 });
    identity.host_version = String(await hostVersion());
  });
  slot.tail = ready.catch(() => {});

  async function atomic(suffix, value, limit) {
    const encoded = JSON.stringify(value);
    if (Buffer.byteLength(encoded) > limit) throw new Error('capacity');
    const temporary = `${prefix}.${boot}.${suffix}.tmp`;
    try {
      await fs.writeFile(temporary, encoded, { mode: 0o600 });
      if (owns()) await fs.rename(temporary, `${prefix}.${suffix}.json`);
    } finally { await fs.rm(temporary, { force: true }).catch(() => {}); }
  }

  function record(event, data = {}) {
    if (stopping || !owns()) return;
    const row = JSON.stringify({ ...data, ...identity, revision: ++revision,
      emitted_at: Date.now() / 1000, event }) + '\n';
    const bytes = Buffer.byteLength(row);
    if (bytes > 64 * 1024 || queueBytes + inFlightBytes + bytes > MIB) {
      queue = [];
      queueBytes = 0;
      gapRevision = revision;
      requested = true;
      return;
    }
    queue.push(row);
    queueBytes += bytes;
  }

  function request(heartbeat = false) {
    if (!owns()) return slot.tail;
    if (heartbeat) health++;
    requested = true;
    if (running) return slot.tail;
    running = true;
    slot.tail = slot.tail.then(async () => {
      while (requested && owns()) {
        requested = false;
        const batch = queue;
        inFlightBytes = queueBytes;
        queue = [];
        queueBytes = 0;
        // Capture the exact state/revision boundary before the first await.
        const currentRevision = revision;
        const lifecycle = stopping ? 'stopped' : 'active';
        const currentHealth = health;
        let snapshot;
        try {
          const agents = observed();
          const value = { ...identity, revision: currentRevision, health_seq: currentHealth,
            snapshot_seq: ++snapshotSequence, lifecycle, coverage: 'observed',
            scope: 'tracked-agents', agents };
          snapshot = JSON.stringify(value);
          if (agents.length > 4096 || Buffer.byteLength(snapshot) > 8 * MIB) snapshot = undefined;
        } catch { snapshot = undefined; }
        try {
          const log = `${prefix}.jsonl`;
          if (batch.length) {
            const stat = await fs.stat(log).catch(() => undefined);
            if (stat && stat.size > MIB) {
              await fs.rm(`${log}.1`, { force: true });
              await fs.rename(log, `${log}.1`);
            }
            await fs.appendFile(log, batch.join(''), { mode: 0o600 });
          }
        } catch { gapRevision = Math.max(gapRevision, currentRevision); }
        inFlightBytes = 0;
        try {
          // Invalid/oversized state still publishes health, explicitly unknown coverage.
          await atomic('snapshot', snapshot ? JSON.parse(snapshot) : { ...identity,
            revision: currentRevision, health_seq: currentHealth, snapshot_seq: snapshotSequence,
            lifecycle, coverage: 'unknown', scope: 'tracked-agents', agents: [] }, 8 * MIB);
        } catch { /* No half-written snapshot can replace the old boundary. */ }
        try {
          await atomic('health', { ...identity, health_seq: currentHealth, lifecycle,
            gap_revision: gapRevision }, 64 * 1024);
        } catch { /* Failed I/O cannot renew the consumer's liveness. */ }
      }
    }).catch(() => {}).finally(() => { running = false; });
    return slot.tail;
  }

  return { record, request, get pending() { return queue.length > 0 || requested; },
    close() {
      if (!stopping) {
        record('bridge/stopped');
        stopping = true;
        return request(true);
      }
      return slot.tail;
    } };
}
