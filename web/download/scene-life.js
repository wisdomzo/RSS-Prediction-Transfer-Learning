/* Small illustrative actors; all motion uses the scene's pausable clock. */
(function () {
  'use strict';
  window.ASSETSceneLife = function (T, world, heightAt, road, obstacles = []) {
    const material = color => new T.MeshStandardMaterial({ color, roughness: 0.7 });
    const dark = material(0x283346), skin = material(0xd6a078), silver = material(0xd3d9de);
    const box = new T.BoxGeometry(1, 1, 1), sphere = new T.SphereGeometry(1, 8, 6);
    function part(parent, geometry, mat, size, position) {
      const mesh = new T.Mesh(geometry, mat); mesh.scale.set(...size); mesh.position.set(...position);
      mesh.castShadow = true; parent.add(mesh); return mesh;
    }
    const walkers = [];
    const phoneRingGeometry=new T.TorusGeometry(1,.016,5,48);phoneRingGeometry.rotateX(Math.PI/2);

    function collider(group,w,d){const o={x:0,z:0,w,d,dynamic:true};obstacles.push(o);group.userData.collider=o;return o;}
    function syncCollider(group,w,d){const o=group.userData.collider;if(!o)return;o.x=group.position.x;o.z=group.position.z;const a=group.rotation.y;o.w=Math.abs(Math.cos(a))*w+Math.abs(Math.sin(a))*d;o.d=Math.abs(Math.sin(a))*w+Math.abs(Math.cos(a))*d;}

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
      const canCall=hiker||walkers.length%2===0;
      let call=null;
      if(canCall){
        const phone=part(limbs[3],box,dark,[.019,.035,.008],[0,-.063,.004]);phone.visible=false;
        const signal=new T.Group();signal.position.set(.01,.222,.004);signal.visible=false;group.add(signal);
        const rings=[];
        for(let n=0;n<3;n++){
          const mat=new T.MeshBasicMaterial({color:0x245aff,toneMapped:false,transparent:true,depthWrite:false});
          const ring=new T.Mesh(phoneRingGeometry,mat);signal.add(ring);rings.push(ring);
        }
        call={active:false,remaining:4+Math.random()*16,elapsed:0,pose:0,phone,signal,rings};
        group.userData.phoneCall=call;
      }
      collider(group,.085,.075);world.add(group); walkers.push({group, limbs, route, phase, speed:hiker?.007:.015,travel:0,call});
    }
    // A visible switchback route on the near slope; hikers stay on the ground.
    const trail = [[-2.8,2.95],[-2.55,2.4],[-1.85,2.2],[-1.55,1.7],[-1.85,1.15],[-1.2,.75],[-.95,.1],[-1.4,-.55]];
    const trailCurve = new T.CatmullRomCurve3(trail.map(([x,z])=>new T.Vector3(x,0,z)));
    const trailPoints = Array.from({length:161},(_,i)=>{const p=trailCurve.getPoint(i/160);p.y=heightAt(p.x,p.z)+.045;return p;});
    world.add(new T.Line(new T.BufferGeometry().setFromPoints(trailPoints),new T.LineBasicMaterial({color:0xc6b18a})));
    for(let i=0;i<4;i++) person(trail,[0xed653f,0x287eb5,0xe4c347,0x82458e][i],true,.12+i*.2);
    person([[2.55,1.7],[2.15,1.35],[1.7,1.65],[1.25,1.3]],0xf2853d,true,.35);
    person([[2.85,-.65],[2.25,-.85],[1.9,-1.2],[1.65,-1.65]],0xd34d72,true,.6);
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
      collider(group,.24,.48);world.add(group);cars.push({group,phase:i/3,direction:i%2?-1:1,travel:0});
    }
    const animals=[];
    const roadPoints=Array.from({length:81},(_,i)=>road.getPoint(i/80));
    function animalSafe(x,z){
      const h=heightAt(x,z);
      return Math.abs(x)<4.3&&z>-4.3&&z<2.9&&h<2.5
        &&Math.abs(heightAt(x+.08,z)-h)<.11&&Math.abs(heightAt(x,z+.08)-h)<.11
        &&!obstacles.some(o=>Math.abs(x-o.x)<o.w/2+.2&&Math.abs(z-o.z)<o.d/2+.2)
        &&!roadPoints.some(p=>Math.hypot(x-p.x,z-p.z)<.4)
        &&Math.hypot(x+3.6,z-2.7)>.45&&Math.hypot(x-3.5,z-2.65)>.45;
    }
    const spawnSites=[];
    for(let x=-3.8;x<=3.8;x+=.3)for(let z=-3.8;z<2.8;z+=.3)if(animalSafe(x,z))spawnSites.push([x,z]);
    const kinds=['rabbit','fox','squirrel'];
    for(let i=0;i<8&&spawnSites.length;i++){
      const [x,z]=spawnSites[Math.floor(Math.random()*spawnSites.length)];
      const kind=i<3?kinds[i]:kinds[Math.floor(Math.random()*kinds.length)];
      const group=new T.Group(),legs=[],fur=material(kind==='fox'?0xc57135:kind==='squirrel'?0x8c5c39:0xc5beb1);
      group.userData.animalKind=kind;
      part(group,sphere,fur,kind==='fox'?[.032,.028,.068]:[.033,.026,.045],[0,.045,0]);
      part(group,sphere,fur,[.025,.026,.027],[0,.073,.043]);
      for(const side of [-1,1]){
        if(kind==='rabbit')part(group,sphere,fur,[.008,.028,.009],[side*.012,.107,.045]);
        else part(group,new T.ConeGeometry(.012,.025,5),fur,[1,1,1],[side*.016,.101,.043]);
        part(group,sphere,dark,[.003,.003,.003],[side*.02,.08,.063]);
        for(const z of [-.033,.033]){
          const leg=new T.Group();leg.position.set(side*.023,.035,z);group.add(leg);
          part(leg,box,fur,[.011,.03,.013],[0,-.015,0]);legs.push(leg);
        }
      }
      if(kind==='rabbit')part(group,sphere,fur,[.014,.014,.014],[0,.046,-.05]);
      if(kind==='fox'){
        const tail=part(group,sphere,fur,[.022,.024,.06],[0,.052,-.092]);tail.rotation.x=-.25;
        part(group,sphere,material(0xe9dfcc),[.016,.018,.022],[0,.067,-.14]);
        part(group,sphere,fur,[.015,.012,.028],[0,.064,.072]);
      }
      if(kind==='squirrel'){
        const tail=part(group,sphere,fur,[.025,.055,.022],[0,.079,-.05]);tail.rotation.x=-.5;
      }
      group.position.set(x,heightAt(x,z)+.016,z);world.add(group);
      animals.push({group,legs,kind,heading:Math.random()*Math.PI*2,timer:.5+Math.random()*2,speed:.15+Math.random()*.2,gait:Math.random()*6});
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
    const ring=new T.TorusGeometry(1,.018,6,80);ring.rotateX(Math.PI/2);
    for(let i=0;i<3;i++){
      const mat=new T.MeshBasicMaterial({color:0x245aff,transparent:true,depthWrite:false,toneMapped:false});
      const mesh=new T.Mesh(ring,mat);world.add(mesh);pulses.push({mesh,mat,phase:i/3});
    }
    let lastElapsed=null;
    return function update(elapsed, player=null) {
      const dt=lastElapsed===null?0:Math.max(0,Math.min(.05,elapsed-lastElapsed));lastElapsed=elapsed;
      animals.forEach(animal=>{
        const {group,legs,kind}=animal;
        if(dt<=0)return;
        animal.timer-=dt;
        if(animal.timer<=0){
          animal.heading+=(Math.random()-.5)*Math.PI*1.5;
          animal.speed=Math.random()<.23?0:.12+Math.random()*(kind==='fox'?.42:.32);
          animal.timer=.6+Math.random()*2.8;
        }
        const x=group.position.x+Math.sin(animal.heading)*animal.speed*dt;
        const z=group.position.z+Math.cos(animal.heading)*animal.speed*dt;
        if(animalSafe(x,z)&&(!player||Math.hypot(x-player.x,z-player.z)>.18)){
          group.position.x=x;group.position.z=z;
        }else{animal.heading+=Math.PI*.65;animal.timer=.3;}
        group.rotation.y=animal.heading;
        animal.gait+=dt*animal.speed*35;
        group.position.y=heightAt(group.position.x,group.position.z)+.016+(kind==='rabbit'&&animal.speed>0?Math.max(0,Math.sin(animal.gait))*.027:0);
        legs.forEach((leg,i)=>{leg.rotation.x=animal.speed>0?Math.sin(animal.gait+(i%2)*Math.PI)*.5:0;});
      });
      walkers.forEach(walker=>{
        const {group,limbs,route,phase,speed,call}=walker;
        if(call){
          if(dt>0){
            call.remaining-=dt;
            if(call.remaining<=0){
              call.active=!call.active;call.elapsed=0;
              call.remaining=call.active?5+Math.random()*6:15+Math.random()*25;
            }
            if(call.active)call.elapsed+=dt;
            call.pose=Math.max(0,Math.min(1,call.pose+(call.active?1:-1)*dt*3));
          }
          call.phone.visible=call.pose>0;
          call.signal.visible=call.active&&call.pose>.8;
          call.rings.forEach((ring,i)=>{
            const phase=(call.elapsed*.75+i/3)%1;
            ring.scale.setScalar(.025+phase*.2);
            ring.material.opacity=Math.sin(phase*Math.PI)*.8;
            ring.material.color.set(world.userData.isNight?0x69caff:0x245aff);
          });
        }
        if(!call||(!call.active&&call.pose===0))walker.travel+=dt;
        const cycle=(walker.travel*speed+phase)%2,t=cycle<=1?cycle:2-cycle;
        const p=route.getPoint(t),tangent=route.getTangent(t);
        if(!player||Math.hypot(player.x-p.x,player.z-p.z)>.16)group.position.set(p.x,heightAt(p.x,p.z)+.045,p.z);
        group.rotation.y=Math.atan2(tangent.x,tangent.z)+(cycle>1?Math.PI:0);
        syncCollider(group,.085,.075);
        limbs.forEach((limb,i)=>{limb.rotation.x=Math.sin(walker.travel*5+phase*12)*(i===0||i===3?1:-1)*.35*(1-(call?call.pose:0));});
        if(call)limbs[3].rotation.z=-2.5*call.pose;
      });
      cars.forEach(car=>{
        const {group,phase,direction}=car;
        const previousTravel=car.travel;car.travel+=dt;
        const progress=(car.travel*.026+phase)%1, t=direction>0?progress:1-progress;
        const p=road.getPoint(t), tangent=road.getTangent(t);
        // Opposite lanes; fade at the model boundary when vehicles enter/leave.
        const x=p.x+tangent.z*.125*direction,z=p.z-tangent.x*.125*direction;
        if(player&&Math.hypot(player.x-x,player.z-z)<.38){car.travel=previousTravel;return;}
        group.position.set(x,heightAt(x,z)+.041,z);
        group.rotation.y=Math.atan2(tangent.x,tangent.z)+(direction<0?Math.PI:0);
        const ahead=road.getPoint(Math.min(1,t+.003)), behind=road.getPoint(Math.max(0,t-.003));
        group.rotation.x=-Math.atan2((heightAt(ahead.x,ahead.z)-heightAt(behind.x,behind.z))*direction,ahead.distanceTo(behind));
        const fade=Math.min(1,progress*40,(1-progress)*40);
        group.scale.set(2.7*fade,2*fade,3.2*fade);
        syncCollider(group,.24*fade,.48*fade);
      });
      const angle=elapsed*.045;
      satellite.position.set(-2.5+Math.sin(angle)*.12,4.85+Math.sin(angle*.7)*.035, -1.4+Math.cos(angle)*.08);
      satellite.rotation.set(.12,Math.sin(angle)*.06,.18);
      pulses.forEach(({mesh,mat,phase})=>{
        const t=(elapsed*.3+phase)%1;
        mesh.position.copy(satellite.position);mesh.position.y-=.22+t*1.35;
        mesh.scale.setScalar(.1+t*.7);mat.opacity=Math.pow(Math.sin(t*Math.PI),.7)*.85;
        mat.color.set(world.userData.isNight?0x69caff:0x245aff);
      });
    };
  };
})();
