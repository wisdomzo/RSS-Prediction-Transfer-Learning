const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const context={window:{},console};vm.createContext(context);
for(const file of ['vendor/three/three.local.js','download/scene-weather.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web',file),'utf8'),context);
test('weather switches reversibly, night lights windows, paused snow stays fixed',()=>{
 const T=context.window.ASSETThree,world=new T.Group();
 const geometry=new T.BufferGeometry();geometry.setAttribute('color',new T.Float32BufferAttribute([.2,.3,.1],3));
 const terrain=new T.Mesh(geometry,new T.MeshStandardMaterial()),windows=new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial());world.add(terrain,windows);
 const original=Array.from(geometry.attributes.color.array),viewport={dataset:{}};
 const weather=context.window.ASSETWeather(T,world,()=>0,true,{ambient:new T.HemisphereLight(),sun:new T.DirectionalLight(),rim:new T.DirectionalLight(),renderer:{},terrain,windows,viewport});
 weather.set('snow','night');weather.update(2);assert.ok(windows.material.emissiveIntensity>0);assert.notDeepEqual(Array.from(geometry.attributes.color.array),original);
 const snow=world.children.find(o=>o.isPoints&&o.geometry.attributes.position.count===240),snapshot=()=>Array.from(snow.geometry.attributes.position.array);
 const paused=snapshot();weather.update(2);assert.deepEqual(snapshot(),paused);weather.update(3);assert.notDeepEqual(snapshot(),paused);assert.ok(snapshot().every(Number.isFinite));
 weather.set('cloudy','day');assert.equal(snow.visible,false);assert.equal(windows.material.emissiveIntensity,0);assert.deepEqual(Array.from(geometry.attributes.color.array),original);
 const cloudGroup=world.children.find(o=>o.isGroup);
 weather.update(10);const cloudSnapshot=()=>cloudGroup.children.map(o=>o.position.toArray());
 assert.ok(cloudGroup.children.every(bank=>bank.children.every(puff=>puff.castShadow)));
 const cloudPaused=cloudSnapshot();weather.update(10);assert.deepEqual(cloudSnapshot(),cloudPaused);
 weather.update(14);assert.notDeepEqual(cloudSnapshot(),cloudPaused);
 weather.set('clear','day');assert.equal(viewport.dataset.weather,'clear');assert.equal(viewport.dataset.time,'day');assert.equal(cloudGroup.visible,false);
});

test('presentation sun aligns with the light from the landscape center',()=>{
 const T=context.window.ASSETThree,world=new T.Group(),sun=new T.DirectionalLight();sun.position.set(-5,12,6);
 const camera=new T.PerspectiveCamera(),geometry=new T.BufferGeometry();geometry.setAttribute('color',new T.Float32BufferAttribute([.2,.3,.1],3));
 const terrain=new T.Mesh(geometry,new T.MeshStandardMaterial()),windows=new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial());world.add(terrain,windows);
 const weather=context.window.ASSETWeather(T,world,()=>0,true,{ambient:new T.HemisphereLight(),sun,rim:new T.DirectionalLight(),renderer:{},terrain,windows,viewport:{dataset:{}},camera});
 const disc=world.children.find(o=>o.isSprite);
 for(const p of [[11,9,13],[-10,6,8],[3,8,-12]]){
  camera.position.set(...p);world.rotation.y+=.2;weather.update(3);
  const center=world.getWorldPosition(new T.Vector3());
  const actual=disc.getWorldPosition(new T.Vector3()).sub(center).normalize();
  const expected=sun.getWorldPosition(new T.Vector3()).sub(sun.target.getWorldPosition(new T.Vector3())).normalize();
  assert.ok(actual.distanceTo(expected)<1e-10);
 }
});
