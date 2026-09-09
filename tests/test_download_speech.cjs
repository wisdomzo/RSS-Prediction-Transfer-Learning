const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('speech fits text, spaces greetings, follows actors and respects pause/visibility',()=>{
 const ctx=new Proxy({measureText:text=>({width:text.length*23})},{get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
 const c={window:{},console,Math:Object.create(Math),document:{createElement:()=>({getContext:()=>ctx})}};c.Math.random=()=>.1;vm.createContext(c);
 for(const f of ['vendor/three/three.local.js','download/scene-speech.js'])vm.runInContext(fs.readFileSync('web/'+f,'utf8'),c);
 const T=c.window.ASSETThree,world=new T.Group(),actors=[];
 for(let i=0;i<5;i++){const p=new T.Group();p.userData.speechHeight=.23;p.position.x=i;world.add(p);actors.push(p);}
 const update=c.window.ASSETSpeech(T,world);update(0);
 const bubbles=world.children.filter(o=>o.name==='speech-bubble');assert.equal(bubbles.length,3);
 let frame=0;const advance=seconds=>{for(let i=0;i<seconds*60;i++)update(++frame/60);};
 advance(12);assert.ok(bubbles.every(o=>!o.visible));advance(4);
 assert.equal(bubbles.filter(o=>o.visible).length,1);
 const shortWidth=bubbles[0].scale.x;assert.ok(shortWidth<.3);
 actors[0].position.x=7;update(frame/60);assert.equal(bubbles[0].position.x,7);
 const snapshot=()=>bubbles.map(o=>[o.visible,...o.position.toArray()]);const paused=snapshot();update(frame/60);assert.deepEqual(snapshot(),paused);
 advance(4);assert.ok(bubbles.every(o=>!o.visible));
 c.Math.random=()=>.99;advance(5);
 const long=bubbles.find(o=>o.visible);assert.ok(long);assert.ok(long.scale.x>shortWidth*2);assert.equal(long.scale.y,.181);
 actors.forEach(p=>p.visible=false);update(frame/60);assert.ok(bubbles.every(o=>!o.visible));
 actors[4].visible=true;let spoke=false;for(let i=0;i<60*20;i++){update(++frame/60);spoke ||= bubbles.some(o=>o.visible&&o.position.x===4);}assert.ok(spoke);
});
