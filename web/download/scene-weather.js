/* Weather and daylight are independent; precipitation uses the shared scene clock. */
(function () {
  'use strict';
  window.ASSETWeather = function (T, world, heightAt, mobile, lights) {
    const {ambient,sun,rim,renderer,terrain,windows,viewport,camera}=lights;
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
    // Transparent six-fold crystal silhouette; antialiased branches replace square points.
    function snowflakeTexture(){
      const size=128,data=new Uint8Array(size*size*4),segments=[];
      for(let arm=0;arm<6;arm++){
        const angle=arm*Math.PI/3,ux=Math.cos(angle),uy=Math.sin(angle);
        segments.push([0,0,ux*.86,uy*.86]);
        for(const radius of [.38,.62])for(const side of [-1,1]){
          const bx=ux*radius,by=uy*radius,a=angle+side*Math.PI/3;
          const length=radius<.5?.22:.17;
          segments.push([bx,by,bx+Math.cos(a)*length,by+Math.sin(a)*length]);
        }
      }
      for(let y=0;y<size;y++)for(let x=0;x<size;x++){
        const px=(x+.5-size/2)/(size/2),py=(y+.5-size/2)/(size/2);let distance=Infinity;
        for(const [ax,ay,bx,by] of segments){
          const dx=bx-ax,dy=by-ay,t=Math.max(0,Math.min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)));
          distance=Math.min(distance,Math.hypot(px-ax-t*dx,py-ay-t*dy));
        }
        const i=(y*size+x)*4;data[i]=240;data[i+1]=248;data[i+2]=255;
        data[i+3]=Math.round(Math.max(0,Math.min(1,(.041-distance)/.018))*255);
      }
      const texture=new T.DataTexture(data,size,size);texture.colorSpace=T.SRGBColorSpace;texture.needsUpdate=true;return texture;
    }
    const snowMaterial=new T.PointsMaterial({map:snowflakeTexture(),color:0xffffff,size:.11,transparent:true,opacity:.92,alphaTest:.015,depthWrite:false,toneMapped:false});
    // Individual sizes and angles avoid a field of identically aligned crystals.
    snowGeometry.setAttribute('flakePhase',new T.Float32BufferAttribute(seeds.map(s=>s.phase*Math.PI*2),1));
    snowMaterial.onBeforeCompile=shader=>{
      shader.vertexShader='attribute float flakePhase; varying float vFlakePhase;\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('gl_PointSize = size;', 'vFlakePhase = flakePhase; gl_PointSize = size * (.7 + .45 * abs(sin(flakePhase)));');
      shader.fragmentShader='varying float vFlakePhase;\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <map_particle_fragment>', `
        vec2 p = gl_PointCoord - vec2(.5);
        float c = cos(vFlakePhase), s = sin(vFlakePhase);
        vec2 uv = mat2(c,-s,s,c)*p + vec2(.5);
        if(any(lessThan(uv,vec2(0.))) || any(greaterThan(uv,vec2(1.)))) discard;
        diffuseColor *= texture2D(map,uv);
      `);
    };
    const snow=new T.Points(snowGeometry,snowMaterial);
    snow.frustumCulled=false;world.add(snow);
    const starPositions=[], starPhases=[];
    for(let i=0;i<220;i++){
      starPositions.push(Math.sin(i*127.1)*5.7,4.6+(i%13)*.19,Math.cos(i*41)*5.7);
      starPhases.push(i*2.399);
    }
    const starGeometry=new T.BufferGeometry();
    starGeometry.setAttribute('position',new T.Float32BufferAttribute(starPositions,3));
    starGeometry.setAttribute('phase',new T.Float32BufferAttribute(starPhases,1));
    const starMaterial=new T.ShaderMaterial({
      transparent:true,depthWrite:false,uniforms:{time:{value:0}},
      vertexShader:'attribute float phase; uniform float time; varying float brightness; void main(){ brightness=.5+.5*sin(time*(.65+.15*sin(phase))+phase); vec4 p=modelViewMatrix*vec4(position,1.); gl_Position=projectionMatrix*p; gl_PointSize=(2.+brightness*1.6); }',
      fragmentShader:'varying float brightness; void main(){ float r=length(gl_PointCoord-.5)*2.; float alpha=(1.-smoothstep(.15,1.,r))*(.35+.65*brightness); gl_FragColor=vec4(.8,.88,1.,alpha); }'
    });
    const stars=new T.Points(starGeometry,starMaterial);world.add(stars);
    // Camera-facing celestial artwork stays recognizable while the terrain rotates.
    function celestialTexture(kind) {
      const size=128,data=new Uint8Array(size*size*4);
      for(let y=0;y<size;y++)for(let x=0;x<size;x++){
        const px=(x+.5-size/2)/(size/2),py=(y+.5-size/2)/(size/2),r=Math.hypot(px,py);
        let alpha=0;
        if(kind==='sun'){
          const angle=Math.atan2(py,px);
          const disc=1-Math.min(1,Math.max(0,(r-.34)/.025));
          const halo=Math.exp(-r*r*6)*.25;
          const rays=Math.pow(Math.max(0,Math.cos(angle*10)),18)*Math.exp(-Math.pow((r-.52)/.14,2))*.38;
          alpha=Math.min(1,disc+halo+rays)*Math.max(0,Math.min(1,(1-r)*8));
        }else{
          const outer=Math.max(0,Math.min(1,(.72-r)*80));
          const cutout=Math.max(0,Math.min(1,(Math.hypot(px-.3,py+.12)-.66)*80));
          alpha=outer*cutout;
        }
        const i=(y*size+x)*4;
        data[i]=kind==='sun'?255:222;data[i+1]=kind==='sun'?211:232;data[i+2]=kind==='sun'?125:244;data[i+3]=Math.round(alpha*255);
      }
      const texture=new T.DataTexture(data,size,size);texture.colorSpace=T.SRGBColorSpace;texture.needsUpdate=true;return texture;
    }
    const sunDisc=new T.Sprite(new T.SpriteMaterial({map:celestialTexture('sun'),transparent:true,depthWrite:false,toneMapped:false}));
    sunDisc.scale.set(1.25,1.25,1);world.add(sunDisc);
    const moon=new T.Sprite(new T.SpriteMaterial({map:celestialTexture('moon'),transparent:true,depthWrite:false,toneMapped:false}));
    moon.scale.set(.65,.65,1);world.add(moon);
    const presentationPosition=new T.Vector3(-3.7,5.5,-2.4);
    function syncCelestialDirection(){
      // Presentation mode: a nearby visible sky marker and one matching
      // directional light, aligned relative to the landscape center.
      sunDisc.position.copy(presentationPosition);
      moon.position.copy(presentationPosition);
      world.updateWorldMatrix(true,false);
      const center=world.localToWorld(new T.Vector3(0,0,0));
      const direction=world.localToWorld(presentationPosition.clone()).sub(center).normalize();
      const position=center.clone().addScaledVector(direction,15);
      sun.position.copy(sun.parent?sun.parent.worldToLocal(position):position);
      sun.target.position.copy(sun.target.parent?sun.target.parent.worldToLocal(center):center);
      sun.target.updateMatrixWorld();
    }
    syncCelestialDirection();
    const materials=new Set();world.traverse(o=>{if(o.material)for(const m of (Array.isArray(o.material)?o.material:[o.material]))if('envMapIntensity' in m)materials.add(m);});
    const environmentLevels=new Map([...materials].map(m=>[m,m.envMapIntensity]));
    return {
      set(weather,time){
        mode=weather;night=time==='night';
        world.userData.isNight=night;
        viewport.dataset.weather=mode;viewport.dataset.time=time;
        if(viewport.ownerDocument)viewport.ownerDocument.documentElement.dataset.time=time;
        sunDisc.visible=!night;moon.visible=night;
        clouds.visible=mode!=='clear';snow.visible=mode==='snow';stars.visible=night&&mode==='clear';
        ambient.intensity=night?.27:mode==='clear'?.85:.68;
        sun.intensity=night?.23:mode==='clear'?1.9:.85;
        sun.color.set(night?0x9cbcff:mode==='clear'?0xffffff:0xd7e2ee);
        rim.intensity=0;renderer.toneMappingExposure=night?.7:.9;
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
        syncCelestialDirection();
        starMaterial.uniforms.time.value=elapsed;
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
