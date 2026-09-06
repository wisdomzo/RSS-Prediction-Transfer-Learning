const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const { terrainHeight } = require('../web/download/scene-math.js');
const context = { window: {}, console };
vm.createContext(context);
for (const file of ['vendor/three/three.local.js', 'download/scene-life.js']) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web', file), 'utf8'), context);
}
test('scene actors have finite transforms and are stable when elapsed time is paused', () => {
  const T = context.window.ASSETThree, world = new T.Group();
  const road = new T.CatmullRomCurve3([new T.Vector3(-4.9,0,3.65),new T.Vector3(0,0,3.85),new T.Vector3(4.9,0,3.25)]);
  const update = context.window.ASSETSceneLife(T, world, terrainHeight, road);
  const snapshot = () => { const result=[];world.traverse(o=>result.push([...o.position.toArray(),...o.rotation.toArray().slice(0,3),...o.scale.toArray()]));return result; };
  update(12);const first=snapshot();update(12);assert.deepEqual(snapshot(),first);
  update(13);assert.notDeepEqual(snapshot(),first);
  for(const t of [0,33,66,100,1000]) { update(t);assert.ok(snapshot().flat().every(Number.isFinite)); }
  // Twelve people, three cars, a satellite, a trail and three signal rings.
  assert.equal(world.children.length,28);
});
test('mixed wildlife roams within mountain bounds and freezes when paused',()=>{
 const T=context.window.ASSETThree,world=new T.Group();
 const road=new T.CatmullRomCurve3([new T.Vector3(-4.9,0,3.65),new T.Vector3(4.9,0,3.25)]);
 const update=context.window.ASSETSceneLife(T,world,terrainHeight,road);
 const animals=world.children.filter(o=>o.userData.animalKind);
 assert.equal(animals.length,8);assert.equal(new Set(animals.map(o=>o.userData.animalKind)).size,3);
 const before=animals.map(o=>o.position.clone());update(0);
 for(let i=1;i<=600;i++)update(i*.04);
 assert.ok(animals.some((o,i)=>o.position.distanceTo(before[i])>.05));
 for(const o of animals){assert.ok(Math.abs(o.position.x)<4.3&&o.position.z>-4.3&&o.position.z<2.9);assert.ok(o.position.y>=terrainHeight(o.position.x,o.position.z));}
 const paused=animals.map(o=>o.position.toArray());update(24);assert.deepEqual(animals.map(o=>o.position.toArray()),paused);
});
test('phone calls stop walking, emit small rings, pause and finish cleanly',()=>{
 const T=context.window.ASSETThree,world=new T.Group();
 const road=new T.CatmullRomCurve3([new T.Vector3(-4.9,0,3.65),new T.Vector3(4.9,0,3.25)]);
 const update=context.window.ASSETSceneLife(T,world,terrainHeight,road);
 const callers=world.children.filter(o=>o.userData.phoneCall);assert.equal(callers.length,9);
 const actor=callers[0],call=actor.userData.phoneCall;update(0);call.remaining=0;
 for(let i=1;i<=20;i++)update(i*.04);
 assert.equal(call.active,true);assert.equal(call.signal.visible,true);assert.equal(call.phone.visible,true);
 const position=actor.position.clone(),elapsed=call.elapsed;update(.8);assert.equal(call.elapsed,elapsed);assert.deepEqual(actor.position,position);
 for(let i=21;i<=30;i++)update(i*.04);assert.deepEqual(actor.position,position);
 call.remaining=0;update(1.24);assert.equal(call.signal.visible,false);
 for(let i=32;i<=50;i++)update(i*.04);assert.equal(call.phone.visible,false);assert.notDeepEqual(actor.position,position);
});
