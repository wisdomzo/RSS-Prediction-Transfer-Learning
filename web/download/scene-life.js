/* Small illustrative actors; all motion uses the scene's pausable clock. */
(function () {
  'use strict';
  window.ASSETSceneLife = function (T, world, heightAt, road) {
    const material = color => new T.MeshStandardMaterial({ color, roughness: 0.7 });
    const dark = material(0x283346), skin = material(0xd6a078), silver = material(0xd3d9de);
    const box = new T.BoxGeometry(1, 1, 1), sphere = new T.SphereGeometry(1, 8, 6);
    function part(parent, geometry, mat, size, position) {
      const mesh = new T.Mesh(geometry, mat); mesh.scale.set(...size); mesh.position.set(...position);
      mesh.castShadow = true; parent.add(mesh); return mesh;
    }
    const walkers = [];
    function person(points, color, hiker, phase) {
      const group = new T.Group(), shirt = material(color);
      part(group, sphere, skin, [.027,.031,.027], [0,.2,0]);
      part(group, box, shirt, [.065,.08,.04], [0,.135,0]);
      const limbs = [];
      for (const side of [-1,1]) {
        const leg = new T.Group(); leg.position.set(side*.019,.1,0); group.add(leg);
        part(leg, box, dark, [.022,.095,.023], [0,-.047,0]); limbs.push(leg);
        const arm = new T.Group(); arm.position.set(side*.044,.17,0); group.add(arm);
        part(arm, box, shirt, [.019,.07,.02], [0,-.035,0]); limbs.push(arm);
      }
      if (hiker) {
        part(group, box, material(0xe9aa35), [.052,.067,.032], [0,.14,-.034]);
        part(group, box, dark, [.007,.17,.007], [.063,.08,.018]);
      }
      const route = new T.CatmullRomCurve3(points.map(([x,z])=>new T.Vector3(x,0,z)));
      world.add(group); walkers.push({group, limbs, route, phase, speed:hiker?.007:.015});
    }
    // A visible switchback route on the near slope; hikers stay on the ground.
    const trail = [[-2.8,2.95],[-2.55,2.4],[-1.85,2.2],[-1.55,1.7],[-1.85,1.15],[-1.2,.75],[-.95,.1],[-1.4,-.55]];
    const trailCurve = new T.CatmullRomCurve3(trail.map(([x,z])=>new T.Vector3(x,0,z)));
    const trailPoints = Array.from({length:161},(_,i)=>{const p=trailCurve.getPoint(i/160);p.y=heightAt(p.x,p.z)+.045;return p;});
    world.add(new T.Line(new T.BufferGeometry().setFromPoints(trailPoints),new T.LineBasicMaterial({color:0xc6b18a})));
    for(let i=0;i<4;i++) person(trail,[0xed653f,0x287eb5,0xe4c347,0x82458e][i],true,.12+i*.2);
    for(let i=0;i<6;i++) {
      const x=-3.6+i*1.25;
      person([[x,3.99],[x+.28,4.02],[x+.5,3.96]],[0x487db0,0xb44b45,0x59764e][i%3],false,i*.14);
    }
    const cars = [];
    const tires = new T.CylinderGeometry(.023,.023,.015,10);
    for(let i=0;i<3;i++) {
      const group=new T.Group();
      part(group,box,material([0xc54136,0x3d76ac,0xe8e0c9][i]),[.072,.045,.15],[0,.045,0]);
      part(group,box,material(0x547e92),[.062,.035,.08],[0,.083,-.008]);
      for(const x of [-.038,.038])for(const z of [-.047,.047]){
        const wheel=part(group,tires,dark,[1,1,1],[x,.026,z]);wheel.rotation.z=Math.PI/2;
      }
      world.add(group);cars.push({group,phase:i/3,direction:i%2?-1:1});
    }
    const satellite=new T.Group();
    part(satellite,box,silver,[.25,.2,.24],[0,0,0]);
    const panel=material(0x245396);
    for(const side of [-1,1]) {
      part(satellite,box,silver,[.3,.025,.025],[side*.22,0,0]);
      part(satellite,box,panel,[.38,.025,.32],[side*.43,0,0]);
      for(let n=0;n<4;n++) part(satellite,box,silver,[.008,.004,.32],[side*.43+(n-1.5)*.09,.015,0]);
    }
    const dish=part(satellite,new T.ConeGeometry(.1,.07,16),silver,[1,1,1],[0,-.14,0]);dish.rotation.z=Math.PI;
    world.add(satellite);
    const pulses=[];
    const ring=new T.BufferGeometry().setFromPoints(Array.from({length:65},(_,i)=>new T.Vector3(Math.cos(i/64*Math.PI*2),0,Math.sin(i/64*Math.PI*2))));
    for(let i=0;i<3;i++){
      const mat=new T.LineBasicMaterial({color:0x397ff1,transparent:true,depthWrite:false});
      const mesh=new T.Line(ring,mat);world.add(mesh);pulses.push({mesh,mat,phase:i/3});
    }
    return function update(elapsed) {
      walkers.forEach(({group,limbs,route,phase,speed})=>{
        const cycle=(elapsed*speed+phase)%2, t=cycle<=1?cycle:2-cycle;
        const p=route.getPoint(t), tangent=route.getTangent(t);
        group.position.set(p.x,heightAt(p.x,p.z)+.045,p.z);
        group.rotation.y=Math.atan2(tangent.x,tangent.z)+(cycle>1?Math.PI:0);
        limbs.forEach((limb,i)=>{limb.rotation.x=Math.sin(elapsed*5+phase*12)*(i===0||i===3?1:-1)*.35;});
      });
      cars.forEach(({group,phase,direction})=>{
        const progress=(elapsed*.026+phase)%1, t=direction>0?progress:1-progress;
        const p=road.getPoint(t), tangent=road.getTangent(t);
        // Opposite lanes; fade at the model boundary when vehicles enter/leave.
        const x=p.x+tangent.z*.047*direction,z=p.z-tangent.x*.047*direction;
        group.position.set(x,heightAt(x,z)+.041,z);
        group.rotation.y=Math.atan2(tangent.x,tangent.z)+(direction<0?Math.PI:0);
        const ahead=road.getPoint(Math.min(1,t+.003)), behind=road.getPoint(Math.max(0,t-.003));
        group.rotation.x=-Math.atan2((heightAt(ahead.x,ahead.z)-heightAt(behind.x,behind.z))*direction,ahead.distanceTo(behind));
        group.scale.setScalar(Math.min(1,progress*40,(1-progress)*40));
      });
      const angle=elapsed*.045;
      satellite.position.set(-2.5+Math.sin(angle)*.12,4.85+Math.sin(angle*.7)*.035, -1.4+Math.cos(angle)*.08);
      satellite.rotation.set(.12,Math.sin(angle)*.06,.18);
      pulses.forEach(({mesh,mat,phase})=>{
        const t=(elapsed*.3+phase)%1;
        mesh.position.copy(satellite.position);mesh.position.y-=.22+t*1.35;
        mesh.scale.setScalar(.1+t*.7);mat.opacity=Math.sin(t*Math.PI)*.45;
      });
    };
  };
})();
