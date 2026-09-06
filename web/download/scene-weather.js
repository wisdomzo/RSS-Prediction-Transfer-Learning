/* Weather and daylight are independent; precipitation uses the shared scene clock. */
(function () {
  'use strict';
  window.ASSETWeather = function (T, world, heightAt, mobile, lights) {
    const {ambient,sun,rim,renderer,terrain,windows,viewport}=lights;
    let mode='clear', night=false;
    const colors=terrain.geometry.getAttribute('color');
    const originalColors=colors.array.slice();
    const cloudMaterial=new T.MeshStandardMaterial({color:0xe2e6ec,roughness:1,transparent:true,opacity:.75,depthWrite:false});
    const clouds=new T.Group();world.add(clouds);
    const puff=new T.SphereGeometry(1,10,7);
    const cloudBanks=[];
    for(let bank=0;bank<3;bank++) {
      const group=new T.Group();clouds.add(group);cloudBanks.push(group);
      for(let i=0;i<6;i++){
        const mesh=new T.Mesh(puff,cloudMaterial);
        // The existing directional-light shadow map follows each moving puff.
        // Hiding the parent cloud group also removes its shadow in clear weather.
        mesh.castShadow=true;
        mesh.position.set((i%3-1)*.53,Math.sin(i*2+bank)*.1,Math.floor(i/3)*.42);
        mesh.scale.set(.6,.2,.38);group.add(mesh);
      }
    }
    const count=mobile?240:500, snowPositions=new Float32Array(count*3), seeds=[];
    for(let i=0;i<count;i++)seeds.push({x:Math.sin(i*127.1)*4.7,z:Math.sin(i*311.7)*4.7,phase:(i*.61803398875)%1});
    const snowGeometry=new T.BufferGeometry();snowGeometry.setAttribute('position',new T.BufferAttribute(snowPositions,3));
    const snow=new T.Points(snowGeometry,new T.PointsMaterial({color:0xffffff,size:.035,transparent:true,opacity:.85,depthWrite:false}));
    snow.frustumCulled=false;world.add(snow);
    const starPositions=[];
    for(let i=0;i<55;i++)starPositions.push(Math.sin(i*127.1)*7,5.3+(i%8)*.23,-3-Math.cos(i*41)*3);
    const stars=new T.Points(new T.BufferGeometry().setAttribute('position',new T.Float32BufferAttribute(starPositions,3)),new T.PointsMaterial({color:0xd6e5ff,size:.026,depthWrite:false}));world.add(stars);
    const materials=new Set();world.traverse(o=>{if(o.material)for(const m of (Array.isArray(o.material)?o.material:[o.material]))if('envMapIntensity' in m)materials.add(m);});
    const environmentLevels=new Map([...materials].map(m=>[m,m.envMapIntensity]));
    return {
      set(weather,time){
        mode=weather;night=time==='night';
        viewport.dataset.weather=mode;viewport.dataset.time=time;
        clouds.visible=mode!=='clear';snow.visible=mode==='snow';stars.visible=night&&mode==='clear';
        ambient.intensity=night?.27:mode==='clear'?.85:.68;
        sun.intensity=night?.23:mode==='clear'?1.9:.85;
        sun.color.set(night?0x9cbcff:mode==='clear'?0xffffff:0xd7e2ee);
        rim.intensity=night?.32:.6;renderer.toneMappingExposure=night?.7:.9;
        materials.forEach(m=>{m.envMapIntensity=environmentLevels.get(m)*(night?.15:1);});
        windows.material.emissive.set(night?0xffbb58:0x000000);windows.material.emissiveIntensity=night?1.7:0;
        cloudMaterial.color.set(night?0x53647e:0xe2e6ec);
        const snowColor=new T.Color(0xe5edf3);
        for(let i=0;i<colors.count;i++)for(let c=0;c<3;c++){
          const blend=mode==='snow'?.76:0;
          colors.array[i*3+c]=originalColors[i*3+c]*(1-blend)+[snowColor.r,snowColor.g,snowColor.b][c]*blend;
        }
        colors.needsUpdate=true;
      },
      update(elapsed){
        cloudBanks.forEach((bank,i)=>{
          const phase=elapsed*.09+i*2.1;
          bank.position.set(Math.sin(phase)*3.6,4.7+i*.18,-.5+Math.cos(phase)*2.6);
          bank.rotation.y=Math.sin(phase*.5)*.12;
        });
        if(mode!=='snow')return;
        seeds.forEach(({x,z,phase},i)=>{
          const drift=Math.sin(elapsed*.35+phase*6.28)*.1;
          const px=x+drift,pz=z;
          snowPositions[i*3]=px;snowPositions[i*3+2]=pz;
          const ground=heightAt(px,pz)+.07;
          snowPositions[i*3+1]=ground+(1-(elapsed*.18+phase)%1)*(5.3-ground);
        });
        snowGeometry.attributes.position.needsUpdate=true;
      }
    };
  };
})();
