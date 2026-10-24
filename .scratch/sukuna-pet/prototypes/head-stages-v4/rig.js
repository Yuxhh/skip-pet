// Prototype geometry: neck center stays fixed; no reference-image translation.
const Rig={
 center:[720,735],sourcePivot:[710,650],top:700,bottom:780,
 matrix(angle,scale=1){const r=angle*Math.PI/180,a=scale*Math.cos(r),b=scale*Math.sin(r),c=-b,d=a,[cx,cy]=Rig.center,[px,py]=Rig.sourcePivot;
  return[a,b,c,d,cx-px-a*(cx-px)-c*(cy-py),cy-py-b*(cx-px)-d*(cy-py)]},
 raw(x,y,m){const [px,py]=Rig.sourcePivot;return[px+m[4]+m[0]*(x-px)+m[2]*(y-py),py+m[5]+m[1]*(x-px)+m[3]*(y-py)]},
 point(x,y,m){const u=Math.max(0,Math.min(1,(y-Rig.top)/(Rig.bottom-Rig.top))),w=1-u*u*(3-2*u),t=Rig.raw(x,y,m);return[x+(t[0]-x)*w,y+(t[1]-y)*w]},
 sample(p,poses){p=((p%41)+41)%41;const bounds=[0,13,24,34,41],i=p<13?0:p<24?1:p<34?2:3,u=(p-bounds[i])/(bounds[i+1]-bounds[i]),t=u*u*(3-2*u),a=poses[i],b=poses[(i+1)%4],mix=k=>a[k]+(b[k]-a[k])*t;return Rig.matrix(mix('angle_deg'),mix('scale'))}
};
