
// TS 11/14/18 overlay for Google Maps satellite view. Paste into the console.
// Anchored to the @lat,lon,Zm token in the URL, so it tracks pan and zoom.
(() => {
const D = {"quad": [[9.9532666, 78.1584818], [9.9532377, 78.1590569], [9.9534254, 78.1591836], [9.9535332, 78.158531]], "road": [[9.9535332, 78.158531], [9.9534446, 78.1590675], [9.9534031, 78.1590654], [9.9534121, 78.1588855], [9.9534211, 78.1587056], [9.9534302, 78.1585257]], "lots": [[[9.9532648, 78.1585173], [9.9532558, 78.1586972], [9.9534211, 78.1587056], [9.9534302, 78.1585257]], [[9.9532558, 78.1586972], [9.9532467, 78.158877], [9.9534121, 78.1588855], [9.9534211, 78.1587056]], [[9.9532467, 78.158877], [9.9532377, 78.1590569], [9.9534031, 78.1590654], [9.9534121, 78.1588855]]], "pins": {"A": [9.953269744086384, 78.158491063731], "B": [9.953243409058897, 78.15905176051328], "C": [9.953420578188025, 78.1591776619198], "D": [9.953529122902225, 78.15853275505997]}};
const R0 = 1866/1478, LAT0 = -1.6675e-6/R0, LON0 = 1.6952941e-6/R0, Z0 = 154;
const ns = 'http://www.w3.org/2000/svg';
function draw(){
  const m = location.pathname.match(/@(-?[\d.]+),(-?[\d.]+),([\d.]+)m/);
  if(!m) return;
  const clat=+m[1], clon=+m[2], k=+m[3]/Z0;
  const latPer=LAT0*k, lonPer=LON0*k, cx=innerWidth/2, cy=innerHeight/2;
  const XY=(la,lo)=>[cx+(lo-clon)/lonPer, cy+(la-clat)/latPer];
  document.getElementById('tslr-ov')?.remove();
  const s=document.createElementNS(ns,'svg'); s.id='tslr-ov';
  s.setAttribute('style','position:fixed;inset:0;width:100vw;height:100vh;z-index:99999;pointer-events:none');
  const poly=(pts,fill,stroke,w,dash)=>{const p=document.createElementNS(ns,'polygon');
    p.setAttribute('points',pts.map(([a,b])=>XY(a,b).join(',')).join(' '));
    p.setAttribute('fill',fill);p.setAttribute('stroke',stroke);p.setAttribute('stroke-width',w);
    if(dash)p.setAttribute('stroke-dasharray',dash);s.appendChild(p);};
  const label=(x,y,t,col,sz)=>{const e=document.createElementNS(ns,'text');
    e.setAttribute('x',x);e.setAttribute('y',y);e.setAttribute('fill',col);
    e.setAttribute('font-size',sz);e.setAttribute('font-weight','700');
    e.setAttribute('text-anchor','middle');e.textContent=t;s.appendChild(e);};
  poly(D.quad,'none','#00e5ff',3);
  poly(D.road,'rgba(255,255,255,.3)','#fff',1.6,'6 4');
  D.lots.forEach((l,i)=>{poly(l,'rgba(0,229,255,.15)','#00e5ff',1.6);
    const c=l.reduce((a,[la,lo])=>[a[0]+la/l.length,a[1]+lo/l.length],[0,0]);
    label(...XY(...c),'LOT '+(i+1),'#00e5ff',22);});
  Object.entries(D.pins).forEach(([n,p])=>{const [x,y]=XY(...p);
    const c=document.createElementNS(ns,'circle');c.setAttribute('cx',x);c.setAttribute('cy',y);
    c.setAttribute('r','5');c.setAttribute('fill','#ff2d55');s.appendChild(c);
    label(x+12,y-7,n,'#ff2d55',20);});
  document.body.appendChild(s);
}
clearInterval(window.__tslrTimer); window.__tslrTimer=setInterval(draw,400); draw();
})();
