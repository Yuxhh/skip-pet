const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=__dirname;
const bounce=vm.runInNewContext(fs.readFileSync(path.join(root,'bounce.js'),'utf8')+';Bounce');
const motion=vm.runInNewContext(fs.readFileSync(path.join(root,'eyes.js'),'utf8')+';Motion');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
new vm.Script(html.split('</script><script>')[1].split('</script>')[0]);
const single=[0,55,110,165,220,500].map(age=>({age_ms:age,...bounce.sample(age),anchor:bounce.point(...bounce.anchor,age)}));
let s=motion.initial();const stages=[];
for(let i=0;i<4;i++){s=motion.next(s);for(let t=0;t<500;t+=4)s=motion.tick(s,4);stages.push({stage:s.stage,eye:s.eye,body:s.body,blinks:s.blinks,clicks:s.clicks})}
let age=Infinity,s2=motion.initial();const rapid=[];
for(let i=0;i<5;i++){s2=motion.next(s2);age=0;rapid.push({click:s2.clicks,stage:s2.stage,age_ms:age,...bounce.sample(age)});for(let t=0;t<45;t+=1){s2=motion.tick(s2,1);age+=1}}
for(let t=0;t<600;t++){s2=motion.tick(s2,1);age+=1}
const out={kind:'prototype numerical observations, not human approval',html_script_syntax:'compiled successfully',single_click:single,sequential_stage_endpoints:stages,rapid_click_restarts:rapid,rapid_final:{stage:s2.stage,clicks:s2.clicks,blinks:s2.blinks,bounce:bounce.sample(age)},disabled_at_peak:bounce.sample(110,false),eyes_unchanged:fs.readFileSync(path.join(root,'eyes.js'),'utf8')===fs.readFileSync(path.join(root,'../head-stages-v4/eyes.js'),'utf8'),rig_unchanged:fs.readFileSync(path.join(root,'rig.js'),'utf8')===fs.readFileSync(path.join(root,'../head-stages-v4/rig.js'),'utf8')};
fs.writeFileSync(path.join(root,'bounce-observations.json'),JSON.stringify(out,null,2));console.log(JSON.stringify(out));
