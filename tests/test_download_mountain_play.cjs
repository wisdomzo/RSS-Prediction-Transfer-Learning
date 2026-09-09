const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {terrainHeight,localTimeOfDay}=require('../web/download/scene-math.js');
test('initial day/night follows local clock at boundaries',()=>{
 for(const [h,want] of [[0,'night'],[5,'night'],[6,'day'],[17,'day'],[18,'night'],[23,'night']])assert.equal(localTimeOfDay(new Date(2026,8,9,h)),want);
});
test('mountain recreation switches with snow, remains behind summit and pauses',()=>{
 const c={window:{},console};vm.createContext(c);
 for(const f of ['vendor/three/three.local.js','download/scene-mountain-play.js'])vm.runInContext(fs.readFileSync('web/'+f,'utf8'),c);
 const T=c.window.ASSETThree,world=new T.Group(),update=c.window.ASSETMountainPlay(T,world,terrainHeight);
 const root=world.getObjectByName('mountain-play'),slide=world.getObjectByName('mountain-slide'),people=root.children.filter(o=>o.userData.speechHeight);
 world.userData.weather='clear';update(3);assert.equal(slide.visible,true);assert.equal(people.filter(o=>o.visible).length,3);
 const snap=()=>people.map(o=>[...o.position.toArray(),...o.scale.toArray()]);const before=snap();update(3);assert.deepEqual(snap(),before);update(4);assert.notDeepEqual(snap(),before);
 world.userData.weather='snow';update(5);assert.equal(slide.visible,false);assert.equal(people.filter(o=>o.visible).length,2);
 for(const p of people.filter(o=>o.visible)){assert.ok(p.position.z<root.userData.summit.z);assert.ok(p.position.y>=terrainHeight(p.position.x,p.position.z)-.02);}
});
