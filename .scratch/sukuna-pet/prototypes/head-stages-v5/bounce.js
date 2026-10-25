// dsh-pet ordinary click pulse, applied after the complete character is composed.
const Bounce={
 duration:220,anchor:[709.5,1108],
 sample(age,enabled=true){const p=Math.max(0,Math.min(1,age/Bounce.duration)),pulse=enabled&&p>0&&p<1?Math.sin(Math.PI*p):0;return {sx:1+.10*pulse,sy:1-.15*pulse,active:enabled&&age<Bounce.duration}},
 point(x,y,age){const {sx,sy}=Bounce.sample(age),[cx,cy]=Bounce.anchor;return[cx+(x-cx)*sx,cy+(y-cy)*sy]}
};
