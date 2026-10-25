// Independent oracle: execute the immutable approved JS, never the Python port.
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import vm from 'node:vm';

const commit = '32c9f985d4467c1527b09c34f6868a3ccd3f85b4';
const root = '.scratch/sukuna-pet/prototypes/head-stages-v5/';
const read = name => execFileSync('git', ['show', `${commit}:${root}${name}`], { encoding: 'utf8' });
const params = JSON.parse(read('motion-parameters.json'));
const source = read('eyes.js') + '\n' + read('rig.js') + '\n' + read('bounce.js');
const template = read('preview.template.html');
const eyeSetup = template.split('\n').filter(line => line.startsWith('const keys=') || line.startsWith('function interpolate(')).join('\n');
const scenarios = [
  ['four_stages_and_hold', [0, 200, 400, 700], [0, 60, 110, 120, 181, 199, 200, 260, 310, 353, 399, 400, 460, 510, 519, 520, 521, 580, 620, 640, 700, 750, 798, 810, 920, 2000]],
  ['mid_motion_retarget', [0, 60], [59, 60, 61, 100, 160, 334, 1000]],
  ['blink_closing_retarget', [0, 200, 400, 460], [459, 460, 461, 500, 520, 600, 640, 1000]],
  ['blink_opening_retarget', [0, 200, 400, 560], [520, 559, 560, 561, 600, 640, 1000]],
  ['rapid_five', [0, 45, 90, 135, 180], [0, 45, 90, 120, 135, 180, 220, 290, 399, 400, 500, 1000, 2000]],
  ['many_target_replacements', Array.from({ length: 20 }, (_, i) => i * 10), [30, 90, 150, 190, 300, 1000, 2000]],
  ['second_blink', [0, 200, 400, 700, 900, 1100, 1300], [1200, 1300, 1419, 1420, 1421, 1540, 2000]],
];
const traces = scenarios.map(([name, clicks, samples]) => {
  const context = vm.createContext({ poses: params.components });
  vm.runInContext(`${source}\n${eyeSetup}\nlet s=Motion.initial(),ellipses=[],bounceAge=Infinity;
    const base={},sprite={},tc={clearRect(){},drawImage(){}},sc=new Proxy({},
      {get:(_,name)=>name==='ellipse'?(...args)=>ellipses.push(args.slice(0,2)):()=>{}});
    function sample(){ellipses=[];eyes(s.eye,Motion.closure(s));return {stage:s.stage,
      holding:!s.moving&&s.bodyAge>=s.bodyMs&&!(s.blinkAge<240),
      eye_phase:Motion.mod(s.eye),head_phase:Motion.mod(s.body),
      right_eye:ellipses[0],left_eye:ellipses[3],
      head_matrix:Rig.sample(s.body,poses),eyelid_closure:Motion.closure(s),
      bounce_scale:[Bounce.sample(bounceAge).sx,Bounce.sample(bounceAge).sy]}}`, context);
  const observations = [];
  for (let at = 0; at <= Math.max(...samples); at++) {
    if (at > 0) vm.runInContext('s=Motion.tick(s,1);bounceAge+=1', context);
    if (clicks.includes(at)) vm.runInContext('s=Motion.next(s);bounceAge=0', context);
    if (samples.includes(at)) observations.push({ at_ms: at, ...vm.runInContext('sample()', context) });
  }
  return { name, clicks_ms: clicks, observations };
});
writeFileSync('tests/fixtures/v5-traces.json', JSON.stringify({
  source_commit: commit, source_files: ['eyes.js', 'rig.js', 'bounce.js', 'motion-parameters.json'],
  sampling_ms: 1,
  note: 'Literal Motion.next/tick, Rig.sample and Bounce.sample output at 1ms; head matrix, phase and bounce tolerance 1e-8. Click resets bounceAge just as frozen preview next() does. No port formulas used as expected values.',
  traces,
}, null, 2) + '\n');
console.log(`Captured ${traces.length} V5 sequences from ${commit}`);
