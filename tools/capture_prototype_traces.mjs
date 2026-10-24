// Rebuild independent behavioural fixtures from the approved JS, never the port.
// Requires the historical Git object locally. Not needed for running/tests.
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import vm from 'node:vm';

const commit = '9eef9e2418d536fe6a5b71235841ae98da64329c';
const root = '.scratch/sukuna-pet/prototypes/bounce-feel/';
const html = execFileSync('git', ['show', `${commit}:${root}stage.template.html`], { encoding: 'utf8' });
const packer = execFileSync('git', ['show', `${commit}:${root}pack_stage_demo.py`], { encoding: 'utf8' });
const rules = html.match(/const StageRules=([\s\S]*?)<\/script>/)[0].replace('</script>', '');
const functions = ['gaze', 'socket', 'blinkValue', 'paintSprite', 'beginStageThree', 'next', 'tick']
  .map(name => html.split('\n').find(line => line.startsWith(`function ${name}(`))).join('\n');
const eyeKeys = JSON.parse(packer.match(/assets\['eyeKeys'\]=(\[.*\])/)[1]);
const scenarios = [
  ['ordinary_cycle', [0, 200, 400, 700], [100, 200, 250, 333, 400, 460, 520, 580, 640, 720, 760, 800, 5000]],
  ['mid_motion_retarget', [0, 60], [60, 100, 160, 400, 1400]],
  ['blink_closing_click', [0, 200, 400, 460], [400, 460, 500, 520, 640, 1000]],
  ['blink_opening_click', [0, 200, 400, 560], [400, 520, 560, 600, 640, 1000]],
  ['rapid_across_cycle', [0, 20, 40, 60, 80], [20, 40, 60, 80, 120, 240, 1000, 5000]],
  ['many_clicks_replace_target', Array.from({length: 20}, (_, i) => i * 10), [30, 90, 150, 190, 300, 1000, 5000]],
  ['next_cycle_blinks_again', [0, 200, 400, 700, 900, 1100, 1300], [520, 640, 800, 1420, 1540, 5000]],
];
const traces = [];
for (const [name, clicks, samples] of scenarios) {
  const context = vm.createContext({ eyeKeys });
  vm.runInContext(`${rules}
    let state=StageRules.initial(),last=0,autoBefore=false,hidden=false;
    let now=0,blinkStartedAt=-Infinity,blinkCount=0,blinkJumpTo=null;
    const eyeSpeed=3,phaseNames=['0','1','2','3'];
    const assets={eyeKeys,rightEyeStageTwoShift:-12},redrawn={};
    const performance={now:()=>now};
    const log=()=>{},render=()=>{},paint=()=>{},requestAnimationFrame=()=>{};
    let ellipses=[];
    const spriteCtx=new Proxy({}, {get:(_,name)=>name==='ellipse'
      ? (...args)=>ellipses.push(args.slice(0,2)) : ()=>{}});
    ${functions}
    function sample(){
      ellipses=[];paintSprite(state.pos,blinkValue(now));
      return {stage:state.targetStage,holding:!state.moving&&now-blinkStartedAt>=240,
        right_eye:ellipses[0],left_eye:ellipses[3],eyelid_closure:blinkValue(now)};
    }
  `, context);
  const observations = [];
  for (let time = 0; time <= Math.max(...samples); time++) {
    // 1ms virtual rendering removes browser automation latency from timing.
    vm.runInContext(`now=${time};tick(now)`, context);
    if (clicks.includes(time)) vm.runInContext('next()', context);
    if (samples.includes(time)) observations.push({ at_ms: time, ...vm.runInContext('sample()', context) });
  }
  traces.push({ name, clicks_ms: clicks, observations });
}
mkdirSync('tests/fixtures', { recursive: true });
writeFileSync('tests/fixtures/prototype-traces.json', JSON.stringify({
  source_commit: commit, sampling_ms: 1,
  note: 'Literal output of original StageRules/next/tick/paintSprite; allow 0.2 source pixel for 1ms render quantisation.',
  traces,
}, null, 2) + '\n');
console.log(`Captured ${traces.length} reference sequences from ${commit}`);
