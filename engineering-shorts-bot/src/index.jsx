import React from 'react';
import {registerRoot, Composition, Sequence, AbsoluteFill, Audio, staticFile, useCurrentFrame, interpolate, spring} from 'remotion';
import plan from '../public/plan.json';

const W = 1080, H = 1920, FPS = 30;
const ACCENT = '#47dfcc';
const text = {fontFamily:'Arial, sans-serif',color:'#f4f8ff'};

const Icon = ({topic,part,frame}) => {
  const turn = frame * 2.7;
  const stroke = '#8debe3';
  const base = {stroke,strokeWidth:10,fill:'none',strokeLinecap:'round',strokeLinejoin:'round'};
  if (topic === 'jet') return <svg viewBox="0 0 900 580" style={{width:'100%',height:'100%'}}>
    <defs><linearGradient id="jet" x1="0" x2="1"><stop stopColor="#152a4e"/><stop offset="1" stopColor="#385581"/></linearGradient></defs>
    <path d="M100 150 Q500 60 805 170 L805 410 Q510 510 100 430Z" fill="url(#jet)" stroke={stroke} strokeWidth="9"/>
    <path d="M124 207 Q480 155 772 211 M124 370 Q480 430 772 369" {...base} strokeWidth="5" opacity=".6"/>
    <g transform={`translate(235 290) rotate(${turn})`} stroke={stroke} strokeWidth="10" strokeLinecap="round">{Array.from({length:12},(_,i)=><line key={i} x1="0" y1="25" x2="0" y2="-133" transform={`rotate(${i*30})`}/>) }<circle r="27" fill="#f2f7ff"/></g>
    {Array.from({length:4},(_,i)=><g key={i} transform={`translate(${398+i*72} 290) rotate(${turn*(i%2?-1:1)})`} stroke="#d7edff" strokeWidth="7">{Array.from({length:6},(_,j)=><line key={j} x1="0" y1="15" x2="0" y2="-85" transform={`rotate(${j*60})`}/>)}</g>)}
    <path d="M620 245 Q670 198 720 245 L720 335 Q670 380 620 335Z" fill={part==='COMBUSTOR'?'#ff8f37':'#5b718f'} opacity=".85"/>
    {Array.from({length:6},(_,i)=><circle key={i} cx={125+((frame*10+i*125)%670)} cy={195+(i%3)*85} r="8" fill={i%2?'#52e2ed':'#ffa65e'}/>)}
    <text x="450" y="545" textAnchor="middle" fill="#e3f5ff" fontSize="33">ILLUSTRATIVE TURBOFAN CUTAWAY</text>
  </svg>;
  if (topic === 'tunnel') return <svg viewBox="0 0 900 580" style={{width:'100%',height:'100%'}}><path d="M55 470 V210 Q450 -40 845 210 V470" fill="#324157" stroke="#b4a08b" strokeWidth="35"/><g transform={`translate(275 295) rotate(${turn})`}><circle r="147" fill="#40758d" stroke={stroke} strokeWidth="12"/>{Array.from({length:10},(_,i)=><path key={i} d="M-10 -24 L12 -125 L40 -50Z" transform={`rotate(${i*36})`} fill="#d9e8ea"/>)}</g><path d="M400 285 H800 M400 325 H800" {...base}/>{Array.from({length:4},(_,i)=><rect key={i} x={530+i*74} y="255" width="52" height="94" rx="8" fill="#536a77" stroke="#9eeadf"/>)}<text x="450" y="535" textAnchor="middle" fill="#e3f5ff" fontSize="34">CUT • REMOVE • LINE</text></svg>;
  if (topic === 'space') return <svg viewBox="0 0 900 580" style={{width:'100%',height:'100%'}}><defs><linearGradient id="plasma"><stop stopColor="#ed593b"/><stop offset="1" stopColor="#ffbe55"/></linearGradient></defs><g transform={`translate(${20*Math.sin(frame/23)} ${6*Math.sin(frame/12)})`}><path d="M310 160 Q450 95 590 160 L632 390 Q450 510 268 390Z" fill="#bfd3de" stroke="#d5f9ff" strokeWidth="12"/><path d="M268 390 Q450 486 632 390 L640 425 Q450 554 260 425Z" fill="#e78e47" stroke="#ffce70" strokeWidth="11"/>{Array.from({length:12},(_,i)=><path key={i} d={`M${285+i*29} 443 l${(i%2?1:-1)*30} ${55+25*Math.sin(frame/9+i)}`} stroke="url(#plasma)" strokeWidth="11" strokeLinecap="round"/>)}</g><text x="450" y="80" fill="#e3f5ff" fontSize="38" textAnchor="middle">HEAT SHIELD • CONCEPT DIAGRAM</text></svg>;
  if (topic === 'submarine') return <svg viewBox="0 0 900 580" style={{width:'100%',height:'100%'}}><path d="M70 280 Q120 175 450 208 Q720 213 825 285 Q712 377 440 367 Q135 355 70 280Z" fill="#3d6681" stroke={stroke} strokeWidth="10"/><path d="M358 210 V133 H514 V211" fill="#456b89" stroke={stroke} strokeWidth="8"/><path d="M105 280 H795 M235 250 V337 M650 244 V337" stroke="#d0f1ff" strokeWidth="6" opacity=".75"/>{Array.from({length:5},(_,i)=><circle key={i} cx={220+i*92} cy={295+7*Math.sin(frame/9+i)} r="15" fill="#7bd5ed"/>)}<path d="M120 390 Q440 455 780 390" {...base} strokeDasharray="20 20"/><text x="450" y="540" fill="#e3f5ff" fontSize="34" textAnchor="middle">BALLAST • TRIM • CONTROL PLANES</text></svg>;
  if (topic === 'crane') return <svg viewBox="0 0 900 580" style={{width:'100%',height:'100%'}}><g {...base} strokeWidth="9"><path d="M260 510 L275 100 H475 L490 510Z M275 100 L475 510 M475 100 L275 510 M269 220 H481 M266 325 H484 M262 430 H488"/><path d="M140 120 H820 L860 143 H135Z M365 117 V60 H485 V120 M815 140 V385"/><path d="M785 385 H846 V423 H784Z" fill="#dbad55"/></g><rect x="241" y={210+Math.sin(frame/20)*12} width="270" height="90" fill="#edb861" opacity=".6"/><text x="450" y="555" fill="#e3f5ff" fontSize="33" textAnchor="middle">HYDRAULIC CLIMBING FRAME</text></svg>;
  return <svg viewBox="0 0 900 580" style={{width:'100%',height:'100%'}}><g transform={`translate(0 ${5*Math.sin(frame/12)})`}><rect x="225" y="110" width="450" height="365" rx="52" fill="#eb783f" stroke="#ffdb79" strokeWidth="13"/><rect x="280" y="165" width="340" height="255" rx="28" fill="#536176" stroke="#e5efff" strokeWidth="9"/><rect x="342" y="223" width="218" height="140" rx="15" fill="#85b5c3" stroke={stroke} strokeWidth="7"/>{Array.from({length:5},(_,i)=><path key={i} d={`M${350+i*40} 195 V221 M${350+i*40} 365 V390`} stroke="#b9e8ee" strokeWidth="6"/>)}</g><text x="450" y="545" fill="#e3f5ff" fontSize="33" textAnchor="middle">PROTECTED MEMORY • DIAGRAM</text></svg>;
};

const Scene = ({scene,topic,number,total}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame,[0,8,scene.durationInFrames-7,scene.durationInFrames],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom = interpolate(frame,[0,scene.durationInFrames],[0.97,1.035],{extrapolateRight:'clamp'});
  const words=scene.line.trim().split(/\s+/);
  const spokenFrame=Math.min(frame,scene.durationInFrames-11);
  const pos=Math.floor(spokenFrame/Math.max(1,scene.durationInFrames-11)*words.length);
  const index=Math.min(Math.floor(pos/6)*6,Math.max(0,words.length-6));
  const caption=words.slice(index,index+6).join(' ');
  return <AbsoluteFill style={{opacity,background:'radial-gradient(circle at 50% 35%,#153c59 0%,#081426 55%,#050b17 100%)',...text}}>
    <div style={{position:'absolute',top:115,left:70,right:70,color:ACCENT,fontSize:31,letterSpacing:5,fontWeight:900}}>ENGINEERING / EXPLAINED</div>
    <div style={{position:'absolute',top:185,left:72,right:65,fontWeight:900,fontSize:63,lineHeight:1.14,textTransform:'uppercase'}}>{scene.label}</div>
    <div style={{position:'absolute',top:370,left:58,right:58,height:700,transform:`scale(${zoom})`,border:'2px solid #2f6787',borderRadius:52,background:'linear-gradient(145deg,#0d2e45,#0a1727)',boxShadow:'0 0 90px #062438'}}>
      <div style={{position:'absolute',top:42,left:35,color:'#a3e9e8',fontSize:30,letterSpacing:3,fontWeight:800}}>{scene.part}</div>
      <div style={{position:'absolute',top:105,left:20,right:20,height:550}}><Icon topic={topic} part={scene.part} frame={frame}/></div>
    </div>
    <div style={{position:'absolute',top:1150,left:85,right:85,textAlign:'center',fontSize:51,fontWeight:900,lineHeight:1.24,minHeight:170,textShadow:'0 5px 20px #000'}}>{caption}</div>
    <div style={{position:'absolute',bottom:255,left:80,right:80,height:4,background:'#17465e'}}><div style={{height:4,width:`${100*(frame/scene.durationInFrames)}%`,background:ACCENT}}/></div>
    <div style={{position:'absolute',bottom:175,left:80,right:80,display:'flex',justifyContent:'space-between',fontSize:26,color:'#a8c6d0',fontWeight:700}}><span>HOW IT WORKS</span><span>{String(number+1).padStart(2,'0')} / {String(total).padStart(2,'0')}</span></div>
    <Audio src={staticFile(scene.audio)} volume={1}/>
  </AbsoluteFill>;
};

const Video = () => <AbsoluteFill style={{background:'#050b17'}}>{plan.scenes.map((scene,i)=><Sequence key={i} from={scene.fromFrame} durationInFrames={scene.durationInFrames}><Scene scene={scene} topic={plan.id} number={i} total={plan.scenes.length}/></Sequence>)}</AbsoluteFill>;

const Root = () => <Composition id="EngineeringShort" component={Video} durationInFrames={plan.totalFrames} fps={FPS} width={W} height={H}/>;
registerRoot(Root);
