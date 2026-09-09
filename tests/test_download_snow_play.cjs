const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {terrainHeight}=require('../web/download/scene-math.js');
test('snow activities spawn on terrain, animate, pause, and hide outside snow',()=>{
 const c={window:{},console};vm.createContext(c);
 for(const f of ['vendor/three/three.local.js','download/scene-environment.js','download/scene-snow-play.js'])vm.runInContext(fs.readFileSync('web/'+f,'utf8'),c);
 const T=c.window.ASSETThree,world=new T.Group();const env=c.window.ASSETNaturalEnvironment(T,world,terrainHeight,true);
 const update=c.window.ASSETSnowPlay(T,world,terrainHeight,env.mainRoad,env.obstacles);
 const root=world.getObjectByName('snow-play');update(0);assert.equal(root.visible,false);
 world.userData.weather='snow';update(1);assert.equal(root.visible,true);assert.equal(root.children.length,2);
 assert.ok(root.children[0].position.distanceTo(root.children[1].position)>=1.2);
 const snapshot=()=>{const a=[];root.traverse(o=>a.push(...o.position.toArray(),...o.rotation.toArray().slice(0,3),o.visible));return a;};
 const before=snapshot();for(let i=1;i<=600;i++)update(1+i/60);assert.notDeepEqual(snapshot(),before);
 const paused=snapshot();update(11);assert.deepEqual(snapshot(),paused);
 world.userData.weather='clear';update(12);assert.equal(root.visible,false);
 world.userData.weather='snow';update(13);assert.equal(root.visible,true);
});
