import React from 'react';
import {registerRoot, Composition, Sequence, AbsoluteFill, Audio, staticFile, useCurrentFrame, interpolate} from 'remotion';
import plan from '../public/plan.json';
import JetMechanism from './JetMechanism.jsx';

const W=1080, H=1920, FPS=30;
const palette={ink:'#061321',card:'#102c42',teal:'#61e0e8',white:'#edf8ff',muted:'#a3c4d3'};

// The other five topics retain their own lightweight animated illustrations.
// All illustrations are schematic: no claim of photorealism or CAD accuracy.
const Illustration=({topic,frame})=>{
  const turn=frame*2.8;
  if(topic==='tunnel') return <svg viewBox="0 0 900 700" width="100%" height="100%"><path d="M42 570 V250 Q450 -80 858 250 V570" fill="#35475a" stroke="#b6a28d" strokeWidth="37"/><g transform={`translate(270 337) rotate(${turn})`}><circle r="168" fill="#3a7894" stroke="#8debe3" strokeWidth="14"/>{Array.from({length:12},(_,i)=><path key={i} d="M-12 -27 L16 -148 L47 -56Z" transform={`rotate(${i*30})`} fill="#d9ecf0"/>)}</g><path d="M433 303 H818 M433 365 H818" stroke="#91e5ed" strokeWidth="11"/><g fill="#6f8a97" stroke="#9de8e4" strokeWidth="5">{Array.from({length:4},(_,i)=><rect key={i} x={480+i*77} y="271" width="52" height="126" rx="6"/>)}</g><path d={`M610 ${450+12*Math.sin(frame/9)} L810 ${450+12*Math.sin(frame/9)}`} stroke="#f7b978" strokeWidth="8" strokeDasharray="18 16"/><text x="450" y="658" textAnchor="middle" fill="#dceff8" fontSize="32">CUTTERHEAD / SEGMENT ERECTOR</text></svg>;
  if(topic==='space') return <svg viewBox="0 0 900 700" width="100%" height="100%"><defs><linearGradient id="plasmaV2"><stop stopColor="#fa783c"/><stop offset="1" stopColor="#ffce6a"/></linearGradient></defs><g transform={`translate(${10*Math.sin(frame/20)} ${7*Math.sin(frame/12)})`}><path d="M286 210 Q449 83 616 210 L644 478 Q459 615 255 472Z" fill="#bcd1d9" stroke="#e4f8fb" strokeWidth="14"/><path d="M255 472 Q462 581 644 478 L655 505 Q453 659 244 505Z" fill="#dd8852" stroke="#ffd17d" strokeWidth="13"/>{Array.from({length:13},(_,i)=><path key={i} d={`M${254+i*34} 527 l${20*Math.sin(frame/11+i)} ${66+20*Math.sin(frame/8+i)}`} stroke="url(#plasmaV2)" strokeWidth="10" strokeLinecap="round"/>)}</g><text x="450" y="95" fill="#e4f6fb" fontSize="35" textAnchor="middle">ABLATIVE / INSULATING SHIELD</text></svg>;
  if(topic==='submarine')return <svg viewBox="0 0 900 700" width="100%" height="100%"><path d="M46 344 Q120 213 472 250 Q743 251 855 345 Q730 453 472 441 Q110 435 46 344Z" fill="#3b647b" stroke="#88e7eb" strokeWidth="13"/><path d="M370 251 V170 H521 V254" fill="#41677e" stroke="#90e5ef" strokeWidth="9"/><path d="M102 345 H812 M226 303 V406 M686 302 V406" stroke="#c0e1ef" strokeWidth="7"/><path d="M110 484 Q468 555 815 484" stroke="#73d1f4" strokeWidth="9" strokeDasharray="20 19" fill="none"/>{Array.from({length:8},(_,i)=><circle key={i} cx={130+i*82} cy={372+Math.sin(frame/10+i)*12} r="13" fill="#61d0ee"/>)}<text x="450" y="645" textAnchor="middle" fill="#d9eff6" fontSize="34">BALLAST TANKS / CONTROL PLANES</text></svg>;
  if(topic==='crane')return <svg viewBox="0 0 900 700" width="100%" height="100%"><g stroke="#8ce5e8" strokeWidth="12" strokeLinejoin="round" fill="none"><path d="M268 608 L288 164 H496 L518 608Z M288 164 L518 608 M496 164 L268 608 M281 290 H503 M274 404 H509 M271 511 H515 M127 168 H841 L862 192 H113Z M379 165 V94 H502 V165 M804 186 V461"/></g><rect x="772" y="462" width="67" height="61" fill="#efc36c"/><rect x="248" y={330+12*Math.sin(frame/15)} width="291" height="94" rx="9" fill="#efc36c" opacity=".65"/><text x="450" y="661" textAnchor="middle" fill="#d9eff6" fontSize="34">HYDRAULIC CLIMBING FRAME</text></svg>;
  return <svg viewBox="0 0 900 700" width="100%" height="100%"><g transform={`translate(0 ${7*Math.sin(frame/14)})`}><rect x="213" y="130" width="478" height="423" rx="56" fill="#e57c41" stroke="#ffca83" strokeWidth="15"/><rect x="281" y="189" width="344" height="291" rx="30" fill="#526b7e" stroke="#d3eaf0" strokeWidth="11"/><rect x="348" y="252" width="210" height="166" rx="17" fill="#8bc0ca" stroke="#8eebeb" strokeWidth="10"/>{Array.from({length:5},(_,i)=><path key={i} d={`M${365+i*42} 222 V252 M${365+i*42} 418 V449`} stroke="#ddf4f8" strokeWidth="8"/>)}</g><text x="450" y="655" textAnchor="middle" fill="#d9eff6" fontSize="33">CRASH-PROTECTED MEMORY</text></svg>;
};

const Scene=({scene,topic,number,total})=>{
  const frame=useCurrentFrame();
  const duration=scene.durationInFrames;
  const appear=interpolate(frame,[0,8,duration-8,duration],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const words=scene.line.trim().split(/\s+/);
  // Approximate caption chunks; phoneme/word timestamps are not yet available.
  const wordIndex=Math.min(words.length-1,Math.floor(frame/Math.max(1,duration-11)*words.length));
  const start=Math.floor(wordIndex/5)*5;
  const caption=words.slice(start,start+5).join(' ');
  const visualZoom=interpolate(frame,[0,duration],[1,1.025],{extrapolateRight:'clamp'});
  return <AbsoluteFill style={{opacity:appear,color:palette.white,fontFamily:'Arial, sans-serif',background:'radial-gradient(ellipse at 50% 39%,#174462 0%,#07182a 67%,#040d17 100%)'}}>
    <div style={{position:'absolute',top:79,left:70,right:70,display:'flex',alignItems:'center',justifyContent:'space-between',fontSize:29,fontWeight:800,letterSpacing:3,color:palette.teal}}><span>HOW IT WORKS</span><span style={{color:palette.muted}}>{String(number+1).padStart(2,'0')} / {String(total).padStart(2,'0')}</span></div>
    <div style={{position:'absolute',top:151,left:70,right:68,fontSize:61,fontWeight:900,lineHeight:1.12,letterSpacing:0.2,textTransform:'uppercase',maxHeight:166,overflow:'hidden'}}>{scene.label}</div>
    <div style={{position:'absolute',top:329,left:40,right:40,height:1045,border:'3px solid #285872',borderRadius:44,overflow:'hidden',background:'linear-gradient(160deg,#123249,#061928)',boxShadow:'0 12px 65px #01070d',transform:`scale(${visualZoom})`}}>
      {topic==='jet'?<JetMechanism part={scene.part} frame={frame}/>:<><div style={{position:'absolute',top:40,left:43,right:43,fontSize:31,letterSpacing:2,color:palette.teal,fontWeight:800}}>{scene.part}</div><div style={{position:'absolute',top:100,left:33,right:33,height:790}}><Illustration topic={topic} frame={frame}/></div><div style={{position:'absolute',bottom:37,left:43,right:43,fontSize:27,color:palette.muted}}>ILLUSTRATIVE MECHANISM • NOT TO SCALE</div></>}
    </div>
    <div style={{position:'absolute',top:1430,left:68,right:68,minHeight:166,display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',fontSize:54,fontWeight:900,lineHeight:1.17,textShadow:'0 4px 17px #000'}}>{caption}</div>
    <div style={{position:'absolute',bottom:185,left:78,right:78,height:7,borderRadius:8,background:'#214057',overflow:'hidden'}}><div style={{width:`${Math.max(0,Math.min(100,100*frame/duration))}%`,height:'100%',background:palette.teal}}/></div>
    <div style={{position:'absolute',bottom:115,left:79,right:79,display:'flex',justifyContent:'space-between',fontSize:27,fontWeight:700,color:palette.muted}}><span>ENGINEERING / EXPLAINED</span><span>2D CUTAWAY</span></div>
    <Audio src={staticFile(scene.audio)} volume={1}/>
  </AbsoluteFill>;
};
const Video=()=> <AbsoluteFill style={{background:palette.ink}}>{plan.scenes.map((scene,i)=><Sequence key={i} from={scene.fromFrame} durationInFrames={scene.durationInFrames}><Scene scene={scene} topic={plan.id} number={i} total={plan.scenes.length}/></Sequence>)}</AbsoluteFill>;
registerRoot(()=><Composition id="EngineeringShort" component={Video} durationInFrames={plan.totalFrames} fps={FPS} width={W} height={H}/>);
