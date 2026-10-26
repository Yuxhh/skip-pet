// Real asynchronous plugin output, with only the host event source substituted.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { pathToFileURL } from 'node:url';
const directory = path.resolve(process.argv[2]);
process.env.SUKUNA_PET_BRIDGE_DIR = directory;
const { apply } = await import(pathToFileURL(path.resolve('src/sukuna_pet/integrations/dsh-bridge/index.js')));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const events = new EventEmitter();
const agentEvents = new EventEmitter();
const dispose = [];
const session = { id: 'root' };
const agent = { id: 'root', session, status: 'idle', ctx: {
  on(type, fn) { agentEvents.on(type, fn); return () => agentEvents.off(type, fn); },
} };
const ctx = { agents: { list: () => [agent], isOwnedBy: () => false },
  sessionProjections: { stateOf: () => ({ lastTurn: 0, openTurnStartSeq: null }) },
  on(type, fn) { events.on(type, fn); return () => events.off(type, fn); },
  effect(fn) { dispose.push(fn()); } };
apply(ctx);
await pause(1200);
const prefix = path.join(directory, `dsh-${process.pid}`);
const health = JSON.parse(await fs.readFile(`${prefix}.health.json`, 'utf8'));
const snapshot = JSON.parse(await fs.readFile(`${prefix}.snapshot.json`, 'utf8'));
assert.equal(health.schema_version, 1);
assert.equal(health.owner, '@sukuna-pet/dsh-bridge');
assert.ok(health.health_seq >= 2);
for (const field of ['user_id', 'profile_id', 'process_start_id', 'instance_id', 'boot_id', 'host_version', 'plugin_version']) {
  assert.equal(typeof health[field], 'string');
  assert.ok(health[field]);
  assert.equal(health[field], snapshot[field]);
}
assert.equal(snapshot.coverage, 'observed');
assert.equal(snapshot.scope, 'tracked-agents');
const send = (type, data) => events.emit('session/event', session, { type, data });
send('turn/start', { turn: 2 });
send('turn/start', { turn: 1 }); // A delayed older start cannot reset observed current state.
await pause(150);
assert.equal(JSON.parse(await fs.readFile(`${prefix}.snapshot.json`, 'utf8')).agents[0].turn_id, 2);
// Overflow a single 80ms window without allowing disk to catch up.
for (let i = 0; i < 12000; i++) send('step/start', { turn: 2, secret: 'DO_NOT_EXPORT' });
await pause(1200);
const overflowHealth = JSON.parse(await fs.readFile(`${prefix}.health.json`, 'utf8'));
assert.ok(overflowHealth.gap_revision > 0);
assert.ok(JSON.parse(await fs.readFile(`${prefix}.snapshot.json`, 'utf8')).revision >= 12000);
let lines = (await fs.readFile(`${prefix}.jsonl`, 'utf8')).trim().split('\n');
assert.ok(lines.every(line => Buffer.byteLength(line) + 1 <= 65536));
assert.ok(!lines.join('').includes('DO_NOT_EXPORT'));
// More batches force real NTFS rename/recreate rotation, keeping only .1.
for (let batch = 0; batch < 4; batch++) {
  for (let i = 0; i < 900; i++) send('step/start', { turn: 2 });
  await pause(120);
}
assert.ok((await fs.stat(`${prefix}.jsonl.1`)).size <= 2 * 1024 * 1024);
assert.ok((await fs.stat(`${prefix}.jsonl`)).size <= 2 * 1024 * 1024);
assert.ok(!(await fs.readdir(directory)).some(file => file.endsWith('.2')));
// Replace the plugin in this same PID; the new boot owns all later publications.
const oldBoot = overflowHealth.boot_id;
for (const fn of dispose) await fn();
dispose.length = 0;
apply(ctx);
send('turn/start', { turn: 3 });
await pause(1200);
const reloaded = JSON.parse(await fs.readFile(`${prefix}.health.json`, 'utf8'));
assert.notEqual(reloaded.boot_id, oldBoot);
assert.ok(reloaded.boot_started_at > overflowHealth.boot_started_at);
assert.equal(JSON.parse(await fs.readFile(`${prefix}.snapshot.json`, 'utf8')).agents[0].turn_id, 3);
for (const fn of dispose) await fn();
await pause(150);
assert.equal(JSON.parse(await fs.readFile(`${prefix}.health.json`, 'utf8')).lifecycle, 'stopped');
console.log('Versioned identity, independent health, atomic observed boundary and exit passed');
