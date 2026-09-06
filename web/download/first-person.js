/* Ground-level navigation. Inputs stay scoped to the scene, never the page forms. */
(function () {
  'use strict';
  window.ASSETFirstPerson = function (T, camera, controls, canvas, heightAt, obstacles, schedule) {
    const button=document.getElementById('first-person'),pad=document.getElementById('walk-controls');
    const hint=document.getElementById('scene-help').lastElementChild,originalHint=hint.innerHTML;
    const keys=new Set(),touchKeys=new Set();let active=false,yaw=0,pitch=0,last=null,drag=null,saved;
    const zoomButtons=['zoom-in','zoom-out'].map(id=>document.getElementById(id));
    function clear(){keys.clear();touchKeys.clear();drag=null;last=null;}
    function look(){camera.rotation.set(pitch,yaw,0,'YXZ');}
    function set(value){
      if(active===value)return;
      clear();active=value;button.setAttribute('aria-pressed',String(active));pad.hidden=!active;
      button.innerHTML=active?'全景に戻る<small lang="en">Exit first person</small>':'一人称<small lang="en">First person</small>';
      zoomButtons.forEach(b=>b.disabled=active);
      if(active){
        controls.enableDamping=false;controls.update();controls.enableDamping=true;
        saved={position:camera.position.clone(),quaternion:camera.quaternion.clone(),target:controls.target.clone(),fov:camera.fov,near:camera.near};
        controls.enabled=false;camera.near=.015;camera.fov=65;camera.position.set(0,heightAt(0,3.82)+.2,3.82);yaw=0;pitch=0;look();
        hint.innerHTML='WASD・矢印で移動、ドラッグで見回す<small lang="en">Move: WASD / arrows · Look: drag · Esc: exit</small>';
      }else{
        camera.position.copy(saved.position);camera.quaternion.copy(saved.quaternion);camera.fov=saved.fov;camera.near=saved.near;
        controls.target.copy(saved.target);controls.enabled=true;controls.update();hint.innerHTML=originalHint;
      }
      canvas.setAttribute('aria-label',active?'一人称ビュー。WASD・矢印で移動、ドラッグで見回す、Escapeで終了。 / First person: WASD or arrows to move, drag to look, Escape to exit.':'3D terrain: drag to rotate, plus/minus to zoom, Home to reset.');
      camera.updateProjectionMatrix();canvas.focus({preventScroll:true});schedule();
    }
    button.disabled=false;button.addEventListener('click',()=>set(!active));
    const movement=['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'];
    canvas.addEventListener('keydown',e=>{if(!active)return;if(e.code==='Escape'){e.preventDefault();set(false);}else if(movement.includes(e.code)){e.preventDefault();keys.add(e.code);schedule();}});
    canvas.addEventListener('keyup',e=>keys.delete(e.code));canvas.addEventListener('blur',()=>keys.clear());window.addEventListener('blur',clear);
    document.addEventListener('visibilitychange',()=>{if(document.hidden)clear();});
    canvas.addEventListener('pointerdown',e=>{if(!active||e.button>0)return;drag={id:e.pointerId,x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{if(!active||!drag||drag.id!==e.pointerId)return;yaw-=(e.clientX-drag.x)*.004;pitch=Math.max(-1.2,Math.min(1.2,pitch-(e.clientY-drag.y)*.004));drag.x=e.clientX;drag.y=e.clientY;look();schedule();});
    for(const event of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(event,()=>{drag=null;});
    for(const b of pad.querySelectorAll('[data-walk]')){
      b.addEventListener('pointerdown',e=>{e.preventDefault();b.setPointerCapture(e.pointerId);touchKeys.add(b.dataset.walk);schedule();});
      for(const event of ['pointerup','pointercancel','lostpointercapture'])b.addEventListener(event,()=>touchKeys.delete(b.dataset.walk));
    }
    function allowed(x,z){return Math.abs(x)<4.85&&Math.abs(z)<4.85&&!obstacles.some(o=>Math.abs(x-o.x)<o.w/2+.055&&Math.abs(z-o.z)<o.d/2+.055);}
    return {get active(){return active;},exit(){set(false);},update(now){
      if(!active){last=null;return;}const dt=last===null?0:Math.min(.04,Math.max(0,(now-last)/1000));last=now;
      const down=(a,b)=>keys.has(a)||keys.has(b)||touchKeys.has(a);
      let forward=Number(down('KeyW','ArrowUp'))-Number(down('KeyS','ArrowDown')),side=Number(down('KeyD','ArrowRight'))-Number(down('KeyA','ArrowLeft'));
      const length=Math.hypot(forward,side);if(!length)return;forward/=length;side/=length;
      const dx=(-Math.sin(yaw)*forward+Math.cos(yaw)*side)*dt*.65,dz=(-Math.cos(yaw)*forward-Math.sin(yaw)*side)*dt*.65;
      if(allowed(camera.position.x+dx,camera.position.z))camera.position.x+=dx;
      if(allowed(camera.position.x,camera.position.z+dz))camera.position.z+=dz;
      camera.position.y=heightAt(camera.position.x,camera.position.z)+.2;look();
    }};
  };
})();
