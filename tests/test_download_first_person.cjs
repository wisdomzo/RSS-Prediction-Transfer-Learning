const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function el(){return {listeners:{},innerHTML:'',dataset:{},addEventListener(n,f){(this.listeners[n]??=[]).push(f)},fire(n,e={}){for(const f of this.listeners[n]||[])f(e)},setAttribute(){},focus(){},setPointerCapture(){},querySelectorAll(){return []}};}
test('first person walks on ground, respects obstacles and boundaries, restores camera',()=>{
 const ids=Object.fromEntries(['first-person','walk-controls','scene-help','zoom-in','zoom-out'].map(x=>[x,el()]));ids['scene-help'].lastElementChild=el();
 const context={window:{addEventListener(){}},document:{getElementById:id=>ids[id],addEventListener(){}},console};vm.createContext(context);
 for(const f of ['vendor/three/three.local.js','download/first-person.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web',f),'utf8'),context);
 const T=context.window.ASSETThree,camera=new T.PerspectiveCamera(32),canvas=el(),controls={target:new T.Vector3(),update(){},enabled:true};camera.position.set(11,9,13);const original=camera.position.clone();
 const api=context.window.ASSETFirstPerson(T,camera,controls,canvas,()=>.5,[{x:0,z:2.7,w:1,d:.3}],()=>{});
 ids['first-person'].fire('click');assert.equal(api.active,true);assert.match(ids['first-person'].innerHTML,/一人称を終了/);assert.match(ids['first-person'].innerHTML,/Exit first person/);assert.equal(controls.enabled,false);assert.equal(camera.position.y,.7);
 canvas.fire('keydown',{code:'KeyW',preventDefault(){}});for(let i=0;i<100;i++)api.update(i*40);assert.ok(camera.position.z<3.82&&camera.position.z>2.9);
 canvas.fire('keyup',{code:'KeyW'});canvas.fire('keydown',{code:'KeyD',preventDefault(){}});for(let i=100;i<1000;i++)api.update(i*40);assert.ok(camera.position.x<4.85);
 api.exit();assert.equal(ids['first-person'].innerHTML,'一人称<small lang="en">First person</small>');assert.deepEqual(camera.position,original);assert.equal(camera.fov,32);assert.equal(controls.enabled,true);assert.equal(ids['walk-controls'].hidden,true);
});
