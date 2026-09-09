/* Seasonal recreation on the road-opposite slope of the highest mountain. */
(function(){
 'use strict';
 window.ASSETMountainPlay=function(T,world,heightAt){
  const root=new T.Group();root.name='mountain-play';world.add(root);
  // Locate the actual summit rather than assuming the nominal peak is highest.
  let peak={x:0,z:0,y:0};
  for(let x=-4;x<=4;x+=.08)for(let z=-4;z<=3;z+=.08){const y=heightAt(x,z);if(y>peak.y)peak={x,z,y};}
  const points=[];
  for(let i=0;i<=160;i++){
   const t=i/160,z=peak.z-.65+(-4.65-(peak.z-.65))*t;
   const x=peak.x+Math.sin(t*Math.PI*5)*(.16+.3*t);
   points.push(new T.Vector3(x,heightAt(x,z)+.075,z));
  }
  const route=new T.CatmullRomCurve3(points);root.userData.summit=peak;
  const slide=new T.Group();slide.name='mountain-slide';root.add(slide);
  const material=color=>new T.MeshStandardMaterial({color,roughness:.65});
  const bed=material(0xd6b66a),rail=material(0x507f77),dark=material(0x344257),skin=material(0xd6a078);
  const sphere=new T.SphereGeometry(1,8,6),box=new T.BoxGeometry(1,1,1);
  function part(parent,geo,mat,pos,scale){const o=new T.Mesh(geo,mat);o.position.set(...pos);o.scale.set(...scale);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;}
  const vertices=[],indices=[],edges=[[],[]];
  for(let i=0;i<=240;i++){
   const t=i/240,p=route.getPoint(t),d=route.getTangent(t),normal=new T.Vector3(d.z,0,-d.x).normalize();
   for(let side=0;side<2;side++){
    const q=p.clone().addScaledVector(normal,(side?1:-1)*.052);vertices.push(q.x,q.y,q.z);edges[side].push(q.clone().add(new T.Vector3(0,.033,0)));
   }
   if(i<240){const k=i*2;indices.push(k,k+1,k+2,k+1,k+3,k+2);}
  }
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(vertices,3));geo.setIndex(indices);geo.computeVertexNormals();bed.side=T.DoubleSide;
  part(slide,geo,bed,[0,0,0],[1,1,1]);
  for(const edge of edges)part(slide,new T.TubeGeometry(new T.CatmullRomCurve3(edge),240,.008,5,false),rail,[0,0,0],[1,1,1]);
  for(let i=0;i<=24;i++){const p=route.getPoint(i/24),h=heightAt(p.x,p.z);part(slide,box,rail,[p.x,(p.y+h)/2,p.z],[.025,p.y-h,.025]);}
  const actors=[];
  for(let i=0;i<5;i++){
   const g=new T.Group();root.add(g);g.userData.speechHeight=i<3?.17:.235;
   const coat=material([0xd64d43,0x448bb6,0xd8a633,0x7764ae,0x389889][i]);
   const body=new T.Group();g.add(body);
   part(body,sphere,skin,[0,.12,0],[.021,.023,.021]);part(body,sphere,coat,[0,.14,0],[.024,.014,.024]);
   part(body,box,coat,[0,.08,0],[.046,.055,.032]);
   for(const s of [-1,1]){
    part(body,box,dark,[s*.014,.033,.019],[.016,.025,.06]);
    part(body,box,coat,[s*.033,.079,.013],[.014,.045,.017]).rotation.x=-.55;
   }
   const skis=new T.Group();g.add(skis);
   for(const s of [-1,1]){part(skis,box,coat,[s*.025,.008,0],[.018,.009,.19]);part(skis,box,dark,[s*.05,.065,-.02],[.004,.12,.004]).rotation.x=.25;}
   actors.push({g,body,skis,phase:i/5});
  }
  return function update(elapsed){
   const snowy=world.userData.weather==='snow';slide.visible=!snowy;
   actors.forEach(({g,body,skis,phase},i)=>{
    g.visible=snowy?i>=3:i<3;skis.visible=snowy;if(!g.visible)return;
    const t=(elapsed/(snowy?18:30)+phase)%1,p=route.getPointAt(t),d=route.getTangentAt(t);
    g.position.copy(p);g.position.y+=snowy?-.045:.012;
    g.rotation.set(0,Math.atan2(d.x,d.z),0);
    g.rotateX(-Math.atan2(d.y,Math.hypot(d.x,d.z)));body.rotation.x=snowy?.25:0;
    // Fade the entrance/exit instead of visibly teleporting back uphill.
    const fade=Math.min(1,t*35,(1-t)*35);g.scale.setScalar(fade*(snowy?1.3:1));
   });
  };
 };
})();
