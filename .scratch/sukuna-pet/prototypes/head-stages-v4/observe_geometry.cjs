const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=__dirname,parameters=JSON.parse(fs.readFileSync(path.join(root,'motion-parameters.json'),'utf8'));
const rig=vm.runInNewContext(fs.readFileSync(path.join(root,'rig.js'),'utf8')+';Rig');
let centerMax=0,lowerMax=0,headJoinMax=0,aspectMax=0;
for(let i=0;i<=4100;i++){
 const m=rig.sample(i/100,parameters.components),p=rig.point(...rig.center,m),bottom=rig.point(rig.center[0],rig.bottom,m),top=rig.point(rig.center[0],rig.top,m),head=rig.raw(rig.center[0],rig.top,m);
 centerMax=Math.max(centerMax,Math.hypot(p[0]-rig.center[0],p[1]-rig.center[1]));
 lowerMax=Math.max(lowerMax,Math.hypot(bottom[0]-rig.center[0],bottom[1]-rig.bottom));
 headJoinMax=Math.max(headJoinMax,Math.hypot(top[0]-head[0],top[1]-head[1]));
 aspectMax=Math.max(aspectMax,Math.abs(Math.hypot(m[0],m[1])/Math.hypot(m[2],m[3])-1));
}
const observations={kind:'prototype geometry observations, not user visual approval',sample_count:4101,neck_center:rig.center,max_center_drift_px:centerMax,max_lower_attachment_drift_px:lowerMax,max_head_neck_join_gap_px:headJoinMax,max_face_aspect_deviation:aspectMax,stage3_angle_deg:parameters.components[3].angle_deg,left_right:[-9,9].map(angle=>({angle,center:rig.point(...rig.center,rig.matrix(angle))}))};
fs.writeFileSync(path.join(root,'geometry-observations.json'),JSON.stringify(observations,null,2));
console.log(JSON.stringify(observations));
