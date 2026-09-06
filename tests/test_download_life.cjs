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
  // Ten people, three cars, a satellite, a trail and three signal rings.
  assert.equal(world.children.length,18);
});
