/* Small seasonal actors, driven by the same pausable scene clock. */
(function(){
 'use strict';
 window.ASSETSnowPlay=function(T,world,heightAt,road,obstacles){
  const root=new T.Group();root.name='snow-play';root.visible=false;world.add(root);
  const sphere=new T.SphereGeometry(1,10,8),box=new T.BoxGeometry(1,1,1);
  const mat=color=>new T.MeshStandardMaterial({color,roughness:.95});
  const snow=mat(0xf1f7fc),skin=mat(0xd7a17c),dark=mat(0x334057),orange=mat(0xe77b30);
  function mesh(parent,g,m,p,s){const o=new T.Mesh(g,m);o.position.set(...p);o.scale.set(...s);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;}
  function child(parent,color){
   const g=new T.Group();g.userData.speechHeight=.165;parent.add(g);const coat=mat(color);
   mesh(g,sphere,skin,[0,.121,0],[.021,.023,.021]);
   mesh(g,sphere,coat,[0,.137,0],[.023,.014,.023]);
   mesh(g,sphere,coat,[0,.155,0],[.009,.009,.009]);
   mesh(g,box,coat,[0,.081,0],[.045,.054,.032]);
   const arms=[];
   for(const side of [-1,1]){
    mesh(g,box,dark,[side*.013,.027,0],[.016,.054,.018]);
    const arm=new T.Group();arm.position.set(side*.03,.1,0);g.add(arm);
    mesh(arm,box,coat,[0,-.021,0],[.014,.045,.016]);arms.push(arm);
   }
   g.userData.arms=arms;return g;
  }
  const fight=new T.Group(),build=new T.Group();root.add(fight,build);
  const fighters=[child(fight,0xc84a42),child(fight,0x367fa8),child(fight,0xd7a334),child(fight,0x8365a9)];
  const builders=[child(build,0x429c83),child(build,0xcd6e9c),child(build,0x5b79bf)];
  const balls=fighters.map(()=>mesh(fight,sphere,snow,[0,0,0],[.013,.013,.013]));
  const man=new T.Group();build.add(man);
  mesh(man,sphere,snow,[0,.055,0],[.065,.06,.065]);
  const middle=mesh(man,sphere,snow,[0,.135,0],[.048,.045,.048]);
  const head=new T.Group();head.position.y=.198;man.add(head);
  mesh(head,sphere,snow,[0,0,0],[.032,.032,.032]);
  for(const side of [-1,1])mesh(head,sphere,dark,[side*.011,.008,.028],[.003,.003,.003]);
  mesh(head,new T.ConeGeometry(.006,.025,7),orange,[0,0,.039],[1,1,1]).rotation.x=Math.PI/2;
  const rolling=mesh(build,sphere,snow,[.15,.025,0],[.024,.024,.024]);
  const roads=Array.from({length:81},(_,i)=>road.getPoint(i/80));
  const sites=[];
  for(let x=-4;x<4;x+=.22)for(let z=-3;z<4.5;z+=.22){
   const y=heightAt(x,z),r=.48;
   if(y<0||y>.9)continue;
   if([[r,0],[-r,0],[0,r],[0,-r]].some(([dx,dz])=>Math.abs(heightAt(x+dx,z+dz)-y)>.16))continue;
   if(roads.some(p=>Math.hypot(x-p.x,z-p.z)<.85))continue;
   if(obstacles.some(o=>!o.dynamic&&Math.abs(x-o.x)<o.w/2+r&&Math.abs(z-o.z)<o.d/2+r))continue;
   sites.push([x,z]);
  }
  let active=false,last=null,time=0;
  function locate(){
   const choices=sites.slice();
   for(const group of [fight,build]){
    if(!choices.length)return false;
    const p=choices[Math.floor(Math.random()*choices.length)];group.position.set(p[0],0,p[1]);
    for(let i=choices.length-1;i>=0;i--)if(Math.hypot(choices[i][0]-p[0],choices[i][1]-p[1])<1.2)choices.splice(i,1);
   }
   return true;
  }
  function ground(group,x,z){return heightAt(group.position.x+x,group.position.z+z)+.018;}
  return function update(elapsed){
   const snowy=world.userData.weather==='snow';
   const dt=last===null?0:Math.max(0,Math.min(.05,elapsed-last));last=elapsed;
   if(!snowy){active=false;root.visible=false;return;}
   if(!active){root.visible=locate();active=true;time=0;}else time+=dt;
   if(!root.visible)return;
   fighters.forEach((g,i)=>{
    const side=i<2?-1:1,x=side*.29,z=(i%2-.5)*.31+Math.sin(time*1.5+i)*.025;
    g.position.set(x,ground(fight,x,z),z);g.rotation.y=-side*Math.PI/2;
    const phase=(time*.42+i*.29)%1;g.userData.arms[1].rotation.x=phase<.25?-phase*8:phase<.45?-2+(phase-.25)*14:0;
    const ball=balls[i],t=(phase-.25)/.55;ball.visible=t>=0&&t<=1;
    const bx=x*(1-2*Math.max(0,Math.min(1,t)));
    ball.position.set(bx,ground(fight,bx,z)+.12+Math.sin(Math.max(0,t)*Math.PI)*.18,z);
   });
   const cycle=time%24;
   middle.visible=cycle>7;head.visible=cycle>15;
   man.position.y=ground(build,0,0);
   builders.forEach((g,i)=>{
    const a=i*Math.PI*2/3+time*.12,r=.19+Math.sin(time*.7+i)*.025,x=Math.sin(a)*r,z=Math.cos(a)*r;
    g.position.set(x,ground(build,x,z),z);g.rotation.set(Math.max(0,Math.sin(time*1.5+i))*.35,a+Math.PI,0);
    g.userData.arms.forEach(arm=>arm.rotation.x=-.7-Math.sin(time*1.5+i)*.4);
   });
   const rx=.15+Math.sin(time*.7)*.04;rolling.position.set(rx,ground(build,rx,.07)+.025,.07);rolling.rotation.z=-time;
  };
 };
})();
