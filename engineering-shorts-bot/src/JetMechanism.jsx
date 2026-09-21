import React from 'react';
import {interpolate} from 'remotion';

// Purpose-built 2D educational cutaway, not a CAD model or real footage.
const COLORS = {fan:'#74ecff', bypass:'#5bd4fa', core:'#d8eef6', hot:'#ff985b', turbine:'#f2b366'};
const PARTS = {
  'BYPASS AIR':{x:45,w:812,label:'MOST AIR BYPASSES THE CORE',detail:'A large fan accelerates air through an outer duct.'},
  FAN:{x:70,w:150,label:'FRONT FAN',detail:'The fan moves a large mass of air backward.'},
  COMPRESSOR:{x:250,w:226,label:'MULTI-STAGE COMPRESSOR',detail:'Successive blade stages increase core air pressure.'},
  COMBUSTOR:{x:475,w:150,label:'CONTINUOUS COMBUSTION',detail:'Fuel burns in the core; bypass air remains outside.'},
  TURBINE:{x:625,w:112,label:'TURBINE DRIVES THE SHAFTS',detail:'Hot gas transfers energy to rotating turbine blades.'},
  THRUST:{x:695,w:175,label:'AIR MOVES BACKWARD',detail:'Bypass flow and core exhaust together produce thrust.'},
};
const blade = (x, radius, phase, fill, count=8) => <g transform={`translate(${x} 375) rotate(${phase})`}>{Array.from({length:count},(_,i)=><path key={i} d={`M -7 -16 Q ${radius*.29} -${radius*.53} 10 -${radius} Q 39 -${radius*.83} 17 -${radius*.42} L 10 -17 Z`} transform={`rotate(${i*360/count})`} fill={fill} opacity={i%2?.82:1} stroke="#bdebf3" strokeWidth="1.5"/>)}<circle r="22" fill="#e8f8fa" stroke="#5582a0" strokeWidth="7"/></g>;

export default function JetMechanism({part,frame=0}) {
  const active = PARTS[part] || PARTS['BYPASS AIR'];
  const start = interpolate(frame,[0,12],[0,1],{extrapolateRight:'clamp'});
  const phase = frame*5;
  const particles = Array.from({length:14},(_,i)=>({x:80+((frame*6+i*97)%765), y: i%2?225:526}));
  const core = Array.from({length:12},(_,i)=>({x:255+((frame*5+i*51)%565), y:325+(i%3)*47}));
  return <svg viewBox="0 0 900 900" width="100%" height="100%" role="img" aria-label="Animated simplified cross-section of a high-bypass turbofan engine">
    <defs>
      <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#d4e9f0"/><stop offset=".38" stopColor="#486a82"/><stop offset="1" stopColor="#d0e0e6"/></linearGradient>
      <linearGradient id="hotFlow" x1="0" x2="1"><stop stopColor="#ffd27a"/><stop offset=".6" stopColor="#ff873f"/><stop offset="1" stopColor="#f45f3a"/></linearGradient>
      <linearGradient id="coldFlow" x1="0" x2="1"><stop stopColor="#367ea5"/><stop offset="1" stopColor="#60d9f3"/></linearGradient>
      <filter id="glow"><feGaussianBlur stdDeviation="7"/></filter>
      <marker id="coldArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8Z" fill="#74ddfb"/></marker>
      <marker id="hotArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8Z" fill="#ffa75f"/></marker>
    </defs>
    <rect x="14" y="18" width="872" height="65" rx="20" fill="#102b44" stroke="#36647d"/>
    <text x="40" y="59" fill="#bcebf2" fontSize="27" fontWeight="800" letterSpacing="2">TURBOFAN / SECTION VIEW</text>
    <text x="863" y="59" fill="#74ddfb" textAnchor="end" fontSize="23">2D EXPLAINER</text>

    {/* Air duct and casing deliberately remain visible across every stage. */}
    <path d="M48 174 Q305 97 853 207 L858 568 Q337 658 48 582Z" fill="#19344e" stroke="url(#metal)" strokeWidth="14"/>
    <path d="M77 229 Q380 172 828 243 L828 292 Q382 235 217 290 L217 460 Q402 520 828 471 L828 522 Q380 588 77 532Z" fill="#122a43" stroke="#6796ad" strokeWidth="5"/>
    <path d="M214 300 Q395 266 742 313 L823 339 L823 414 L742 440 Q395 485 214 451Z" fill="#42576a" stroke="#a2c1cf" strokeWidth="5"/>
    <path d="M214 319 Q435 286 740 332 L830 351 L830 397 L740 422 Q420 460 214 431Z" fill="#102337" stroke="#597587" strokeWidth="2"/>
    {/* Bypass air: top and bottom cross-sectional paths. */}
    <path d="M87 241 Q392 187 819 260" stroke="url(#coldFlow)" strokeWidth="29" opacity=".58" fill="none" strokeLinecap="round"/>
    <path d="M87 518 Q397 573 817 506" stroke="url(#coldFlow)" strokeWidth="29" opacity=".58" fill="none" strokeLinecap="round"/>
    {particles.map((p,i)=><g key={`b${i}`} opacity={part==='COMBUSTOR'?.42:1}><path d={`M${p.x-22} ${p.y} h43`} stroke="#7de9fd" strokeWidth="4" strokeLinecap="round" markerEnd="url(#coldArrow)"/>{i%3===0&&<circle cx={p.x-9} cy={p.y} r="4" fill="#d4fbff"/>}</g>)}
    {/* Distinct compressor stages, shaft and gas path. */}
    <path d="M175 375 H706" stroke="#101b29" strokeWidth="25" strokeLinecap="round"/>
    <path d="M175 375 H706" stroke="#c0d3dc" strokeWidth="8" strokeLinecap="round"/>
    <g opacity={part==='FAN'||part==='BYPASS AIR'||part==='THRUST'?1:.65}>{blade(147,124,phase*.58,COLORS.fan,10)}</g>
    {[282,328,374,420].map((x,i)=><g key={`c${i}`} opacity={part==='COMPRESSOR'?1:.78}>{blade(x,48-i*2,phase*(i%2?-1:1),i%2?'#93cfe4':'#c9e5ed',7)}<path d={`M${x+17} 316 l12 26 m-12 92 l12 -26`} stroke="#9dbbca" strokeWidth="7"/></g>)}
    <path d="M474 324 Q518 304 596 323 L601 426 Q527 446 474 424Z" fill="#704e3f" stroke="#eeb889" strokeWidth="5"/>
    {[0,1,2,3,4].map(i=><path key={`fl${i}`} d={`M${490+i*20} ${354+i%2*13} q12 -28 24 0 q-8 9 4 21 q-22 18 -28 -3Z`} fill={i%2?'#ffdd7f':'#ff934a'} opacity={.72+.24*Math.sin(frame/7+i)}/>)}
    {[650,695].map((x,i)=><g key={`t${i}`} opacity={part==='TURBINE'?1:.78}>{blade(x,57+i*4,-phase*.3,'#ffc381',9)}</g>)}
    <path d="M742 315 L830 337 L830 413 L742 437Z" fill="#4b5660" stroke="#b1c7d0" strokeWidth="5"/>
    {core.map((p,i)=><g key={`h${i}`} opacity={p.x>475?.95:.38}><circle cx={p.x} cy={p.y} r={4+(i%3)} fill={p.x>470?'#ffa55e':'#d9f6ff'}/>{i%2===0&&<path d={`M${p.x-14} ${p.y} h27`} stroke={p.x>470?'#ffb679':'#b4e8ef'} strokeWidth="3" markerEnd={p.x>470?'url(#hotArrow)':'url(#coldArrow)'}/>}</g>)}
    {[0,1,2].map((_,i)=><path key={`ex${i}`} d={`M828 ${349+i*21} h44`} stroke="#ffa65e" strokeWidth="7" strokeLinecap="round" markerEnd="url(#hotArrow)"/>)}
    <rect x={active.x} y="162" width={active.w} height="453" rx="22" fill="none" stroke={part==='COMBUSTOR'||part==='TURBINE'?'#ffc07b':'#6ee8fa'} strokeWidth="5" strokeDasharray="15 13" opacity={.7+.3*Math.sin(frame/12)}/>
    <path d={`M${active.x+active.w/2} 619 v45`} stroke="#87e7f2" strokeWidth="5" strokeLinecap="round"/>
    <circle cx={active.x+active.w/2} cy="619" r="8" fill="#dffaff"/>
    <rect x="21" y="674" width="858" height="195" rx="30" fill="#0d2a42" stroke="#326780" strokeWidth="4"/>
    <rect x="40" y="693" width="12" height="150" rx="6" fill={part==='COMBUSTOR'||part==='TURBINE'?'#ffb778':'#64daf3'}/>
    <text x="80" y="739" fontSize="33" fill={part==='COMBUSTOR'||part==='TURBINE'?'#ffca8b':'#8ce9fa'} fontWeight="900" letterSpacing="1">{active.label}</text>
    <foreignObject x="79" y="761" width="745" height="88"><div xmlns="http://www.w3.org/1999/xhtml" style={{fontFamily:'Arial,sans-serif',color:'#ecf8ff',fontWeight:600,fontSize:29,lineHeight:1.17}}>{active.detail}</div></foreignObject>
    <g opacity={start}><path d="M88 618 H825" stroke="#35546a" strokeWidth="2"/></g>
  </svg>;
}
