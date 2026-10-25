// Disposable browser inspection, not a production test suite.
const {chromium}=require('C:/Users/xing/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'}),page=await browser.newPage({viewport:{width:1180,height:950}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
 await page.waitForTimeout(400);
 const observations=[];
 for(const v of ['A','B','C']){
  await page.evaluate(v=>setVariant(v),v);
  await page.selectOption('#scenario','mixed');
  observations.push({variant:v,text:await page.locator('#bubble').innerText()});
  await page.screenshot({path:path.join(__dirname,'preview-'+v+'.png')});
 }
 await page.selectOption('#scenario','inside');observations.push({same_round:await page.locator('#bubble').innerText()});
 for(const s of ['unknown','disconnect']){
  await page.selectOption('#scenario',s);observations.push({scenario:s,hidden:await page.locator('#bubble').isHidden(),moving:await page.evaluate(()=>shouldMove(current()))});
 }
 await page.click('#later');observations.push({disconnect_after_10s:await page.evaluate(()=>shouldMove(current()))});
 await page.selectOption('#scenario','complete');await page.click('#later');observations.push({terminal_expired:await page.locator('#bubble').isHidden()});
 await page.selectOption('#scenario','mixed');await page.selectOption('#policy','change');await page.click('#later');observations.push({change_expired:await page.locator('#bubble').isHidden()});
 await page.selectOption('#policy','stay');
 await page.check('#two');const positions=[];
 for(const size of ['188','271','320'])for(const pos of ['top','left','right','corner','seam']){
  await page.selectOption('#size',size);await page.selectOption('#position',pos);
  positions.push(await page.evaluate(()=>{const b=$('bubble').getBoundingClientRect(),s=$('screen').getBoundingClientRect();return{size:$('size').value,pos:$('position').value,in_bounds:b.left>=s.left&&b.right<=s.right&&b.top>=s.top&&b.bottom<=s.bottom,side:$('bubble').dataset.side,click_through:getComputedStyle($('bubble')).pointerEvents}}));
 }
 await page.selectOption('#mode','click');
 const stageBefore=await page.evaluate(()=>stage);await page.locator('#pet').click();await page.waitForTimeout(380);observations.push({click_advanced:await page.evaluate(prev=>stage!==prev,stageBefore)});
 const pet=await page.locator('#pet').boundingBox();await page.mouse.move(pet.x+pet.width/2,pet.y+pet.height/2);await page.mouse.down();await page.mouse.move(pet.x+pet.width/2-70,pet.y+pet.height/2+35,{steps:8});await page.mouse.up();
 observations.push({drag_stage:await page.evaluate(()=>stage)});
 await page.uncheck('#two');await page.selectOption('#size','271');await page.selectOption('#mode','linked');await page.selectOption('#position','middle');await page.selectOption('#scenario','mixed');await page.evaluate(()=>setVariant('A'));await page.screenshot({path:path.join(__dirname,'preview-A.png')});
 const result={errors,observations,positions,note:'Simulated HTML only; no human verdict, host integration or native multi-DPI validation.'};
 fs.writeFileSync(path.join(__dirname,'observations.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));await browser.close();
})();
