/* Local-only, illustrative training observatory. No model outputs are fabricated. */
(() => {
  'use strict';
  const THREE = window.ASSETThree;
  const style = document.createElement('style');
  style.textContent = `
    .observer-dialog {position:fixed;inset:0;width:100vw;height:100dvh;max-width:none;max-height:none;border:0;padding:0;margin:0;background:#071014;color:#edfafa;overflow:hidden;}
    .observer-dialog::backdrop {background:#071014;}
    .observer-dialog canvas {display:block;width:100%;height:100%;touch-action:none;}
    .observer-hud {position:absolute;inset:20px 24px auto;display:flex;align-items:center;justify-content:space-between;gap:16px;pointer-events:none;}
    .observer-hud h2 {font-size:18px;margin:0 0 5px;letter-spacing:0;}
    .observer-hud p {font-size:12px;margin:0;color:#a4c6cb;}
    .observer-hud button {pointer-events:auto;background:#122c35;color:white;border:1px solid #6396a3;padding:10px 16px;border-radius:6px;cursor:pointer;}
    .observer-hud {z-index:3;}
    .observer-actions {display:flex;gap:8px;align-items:center;}
    .observer-hud .observer-train-button {width:42px;height:42px;padding:9px;display:grid;place-items:center;}
    .observer-train-button img {width:22px;height:22px;filter:invert(1);}
    .observer-train-button[aria-pressed=true] {background:#23685e;border-color:#98e5cf;}
    .observer-train-button:disabled {opacity:.35;filter:grayscale(1);cursor:not-allowed;box-shadow:none;}
    .observer-train-button:not(:disabled) {border-color:#91e7d2;box-shadow:0 0 12px #56d6cc44;}
    .observer-cabin {position:absolute;inset:0;pointer-events:none;opacity:0;z-index:1;}
    .observer-window {position:absolute;inset:-8% -16% 10% 24%;border:14px solid #303532;border-left:22px solid #aca596;border-radius:16px;transform:perspective(1100px) rotateY(-12deg);transform-origin:left center;box-shadow:0 0 0 150vmax #353a3a,inset 0 0 12px #09171965,0 8px 25px #000;}
    .observer-window::after {content:'';position:absolute;left:-22px;right:-14px;bottom:-43px;height:29px;background:linear-gradient(#b6a282,#786b57);border-radius:3px;box-shadow:0 7px 12px #0006;}
    .observer-seat {position:absolute;left:-4%;top:8%;bottom:-12%;width:25%;max-width:330px;background:repeating-linear-gradient(0deg,#363c3d 0px,#363c3d 4px,#535450 5px,#303637 7px);border:10px solid #85867c;border-left:0;border-radius:20px 68px 24px 0;box-shadow:inset -18px 0 25px #0007,12px 0 26px #0007;transform:perspective(800px) rotateY(9deg);}
    .observer-seat::before {content:'';position:absolute;top:0;bottom:36%;left:0;width:20%;background:#dddcd2;border-right:2px dashed #a7a89f;border-radius:0 0 12px 0;}
    .observer-seat::after {content:'';position:absolute;bottom:15%;left:10%;right:9%;height:24%;border:5px solid #8b8d83;border-radius:12px;background:#505754;box-shadow:inset 0 3px 6px #0008;}
    .observer-cabin.reverse-direction {transform:scaleX(-1);}
    .observer-window {border-color:#252b2c;border-left-color:#b6b9b4;box-shadow:0 0 0 3px #080e11,0 0 0 10px #c4c5be,0 0 0 150vmax #525959,inset 0 0 0 3px #0e1518,inset 0 0 24px #10242c44,0 10px 30px #0009;}
    .observer-window::before {content:'';position:absolute;inset:0;background:linear-gradient(112deg,transparent 30%,#e3f6ff0a 31%,transparent 47%);border-top:5px solid #747b78;}
    .observer-window::after {height:35px;background:linear-gradient(#d0d2cb 0%,#b3b9b6 14%,#8f9795 22%,#b8bcb6 72%,#697370 100%);border-top:1px solid #e4e5df;}
    .observer-seat {background:repeating-linear-gradient(0deg,#ffffff08 0px,#ffffff08 1px,transparent 1px,transparent 4px),repeating-linear-gradient(90deg,#233840 0px,#30454b 2px,#263c45 3px,#263c45 5px);border-color:#929d9c;box-shadow:inset -20px 0 35px #07131799,inset 4px 3px 8px #cfdbdc55,10px 0 22px #0008;}
    .observer-seat::before {top:4%;bottom:auto;left:14%;width:70%;height:21%;background:linear-gradient(100deg,#c8cfc9,#f2f0e9 35%,#dedfd6 75%,#bfc8c3);border:0;border-bottom:2px dashed #b2b9b2;border-radius:12px 20px 18px 12px;box-shadow:0 5px 7px #0003;}
    .observer-seat::after {bottom:20%;height:27%;border-color:#7e8b8b;background:linear-gradient(115deg,#7b8989,#536567 40%,#697779);box-shadow:inset 0 0 0 2px #9caaaa55,inset 0 3px 6px #17272b88,0 3px 5px #0006;}
    .observer-seat-seam {position:absolute;inset:29% 9% 10%;border:1px dashed #94a4a366;border-radius:22px;}
    .observer-table-latch {position:absolute;z-index:1;bottom:45%;left:47%;width:14%;height:3%;min-height:12px;border:2px solid #9aa6a5;border-radius:4px;background:#35464b;box-shadow:0 2px 3px #0007;}
    .observer-table-hinge {position:absolute;z-index:1;bottom:20%;left:21%;right:19%;height:5px;background:linear-gradient(#b7c4c3,#546b70);border-radius:3px;}
    .observer-seat-pocket {position:absolute;bottom:5%;left:13%;right:12%;height:12%;background:repeating-linear-gradient(45deg,transparent 0px,transparent 6px,#566a6d 7px,#566a6d 8px),repeating-linear-gradient(-45deg,#1b3035 0px,#1b3035 6px,#566a6d 7px,#566a6d 8px);border:4px solid #748687;border-radius:5px 5px 16px 16px;}
    .observer-armrest {position:absolute;left:14%;bottom:2%;width:13%;height:5%;background:linear-gradient(#8b9693,#485957);border:3px solid #8a9795;border-radius:18px 24px 8px 8px;box-shadow:0 9px 12px #0008;transform:rotate(-8deg);}
    .observer-window {left:17%;}
    .observer-seat {width:18%;max-width:250px;}
    .observer-armrest {left:9%;width:10%;}
    .observer-dialog.train-view .observer-controls,.observer-dialog.train-view .observer-footer {visibility:hidden;}
    @media(max-width:600px) {.observer-window{inset:80px -28% 12% 16%;border-width:10px;border-radius:12px}.observer-seat{top:100px;width:20%;border-width:6px;border-radius:15px 35px 15px 0}.observer-actions{gap:4px}.observer-hud .observer-train-button{flex-shrink:0}}
    .observer-footer {position:absolute;bottom:20px;left:24px;right:24px;display:flex;justify-content:space-between;gap:12px;font:12px sans-serif;color:#bdd9df;pointer-events:none;}
    .observer-legend {display:flex;align-items:center;gap:8px;}
    .observer-controls {position:absolute;bottom:52px;right:24px;display:flex;gap:12px;align-items:center;font:12px sans-serif;color:#d2eced;background:#10212ac9;padding:10px;border-radius:6px;}
    .observer-controls label {display:flex;align-items:center;gap:6px;white-space:nowrap;margin:0;font:12px sans-serif;}
    .observer-controls input[type=checkbox] {width:16px;height:16px;padding:0;margin:0;}
    .observer-controls input[type=range] {width:90px;padding:0;margin:0;accent-color:#56d6cc;}
    .observer-scale {width:110px;height:7px;background:linear-gradient(90deg,#1768ff,#22d9a0,#ffe855,#ff453c);}
    .observer-error {position:absolute;inset:40% 20%;text-align:center;}
    @media(max-width:600px) {.observer-hud{inset:14px 14px auto}.observer-hud h2{font-size:15px}.observer-hud p{max-width:220px}.observer-footer{left:14px;right:14px;flex-wrap:wrap}.observer-legend{font-size:11px}}
  `;
  document.head.appendChild(style);
  let current = null;
  window.trainingObserver = {open(trigger) {
    if (current) return;
    const dialog = document.createElement('dialog');
    dialog.className = 'observer-dialog';
    dialog.setAttribute('aria-label', 'Neural training first-person observatory');
    dialog.innerHTML = `<div class="observer-hud"><div><h2>Neural Training Observatory</h2><p>Illustrative digital twin · Live application log</p></div><button type="button" aria-label="Exit first-person view">Exit View</button></div><div class="observer-footer"><span class="observer-status">Initializing scene</span><span class="observer-legend">Weak <span class="observer-scale"></span> Strong · Illustrative field</span></div>`;
    dialog.insertAdjacentHTML('beforeend','<div class="observer-controls"><label><input type="checkbox" id="observer-heat" checked>Signal field</label><label>Opacity <input id="observer-opacity" type="range" min="0" max="75" value="40" aria-label="Signal field opacity"><output>40%</output></label></div>');
    const exitButton=dialog.querySelector('button');
    const actions=document.createElement('div');actions.className='observer-actions';exitButton.replaceWith(actions);actions.appendChild(exitButton);
    const rideButton=document.createElement('button');rideButton.type='button';rideButton.className='observer-train-button';rideButton.title='Train window view';rideButton.setAttribute('aria-label','Train window view');rideButton.setAttribute('aria-pressed','false');rideButton.innerHTML='<img src="assets/download/train-front.svg" alt="">';actions.prepend(rideButton);
    rideButton.disabled=true;
    const flightButton=rideButton.cloneNode(true);flightButton.title='Waiting for a passing aircraft';flightButton.setAttribute('aria-label','Aircraft window view');flightButton.innerHTML='<img src="assets/download/plane.svg" alt="">';actions.insertBefore(flightButton,exitButton);
    const boatButton=rideButton.cloneNode(true);boatButton.title='Waiting for a passing boat';boatButton.setAttribute('aria-label','Boat view');boatButton.innerHTML='<img src="assets/download/ship.svg" alt="">';actions.insertBefore(boatButton,exitButton);
    dialog.insertAdjacentHTML('beforeend','<div class="observer-cabin" aria-hidden="true"><div class="observer-window"></div><div class="observer-seat"><div class="observer-seat-seam"></div><div class="observer-table-latch"></div><div class="observer-table-hinge"></div><div class="observer-seat-pocket"></div></div><div class="observer-armrest"></div></div>');
    document.body.appendChild(dialog);
    dialog.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    let renderer, frame, resize, lastLog = '', logChangedAt = 0;
    const textures = [], scene = new THREE.Scene();
    function close() {
      cancelAnimationFrame(frame);
      resize?.disconnect();
      scene.traverse(obj => {obj.geometry?.dispose(); for (const mat of [].concat(obj.material || [])) mat.dispose();});
      textures.forEach(texture => texture.dispose());
      renderer?.dispose();
      renderer?.forceContextLoss();
      dialog.close(); dialog.remove();
      document.body.style.overflow = previousOverflow;
      current = null;
      trigger?.focus();
    }
    current = {close};
    exitButton.onclick = close;
    dialog.addEventListener('cancel', event => {event.preventDefault(); close();});
    try {
      renderer = new THREE.WebGLRenderer({antialias:true, alpha:false});
    } catch (error) {
      const message = document.createElement('p');
      message.className = 'observer-error';
      message.textContent = '3D visualization is unavailable. Please enable hardware acceleration. Training continues normally.';
      dialog.appendChild(message); return;
    }
    dialog.prepend(renderer.domElement);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    renderer.setClearColor(0x071014);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const camera = new THREE.PerspectiveCamera(62, 1, .1, 180);
    scene.add(camera);
    resize = new ResizeObserver(() => {const w = dialog.clientWidth, h = dialog.clientHeight; renderer.setSize(w,h); camera.aspect=w/h; camera.fov=w<h?85:62; camera.updateProjectionMatrix();});
    resize.observe(dialog);
    scene.fog = new THREE.FogExp2(0x071014, .009);
    scene.add(new THREE.HemisphereLight(0xc6eaff,0x344640,3));
    const sun = new THREE.DirectionalLight(0xffebcc,3); sun.position.set(-20,35,20); scene.add(sun);
    sun.castShadow=true; sun.shadow.mapSize.set(2048,2048);
    Object.assign(sun.shadow.camera,{left:-28,right:28,top:28,bottom:-28,near:1,far:100});
    sun.shadow.normalBias=.035;
    const rim = new THREE.PointLight(0x32caff,90,50); rim.position.set(0,12,5); scene.add(rim);
    const material = (color, extra={}) => new THREE.MeshStandardMaterial({color,roughness:.55,...extra});
    const teal = material(0x39c9ce,{emissive:0x126478,emissiveIntensity:.5});
    const white = material(0xd6e7e6,{metalness:.35});
    function mesh(geometry, mat, x=0,y=0,z=0, parent=scene) {const obj=new THREE.Mesh(geometry,mat); obj.position.set(x,y,z); obj.castShadow=!mat.transparent;obj.receiveShadow=!mat.transparent;parent.add(obj); return obj;}
    function box(x,y,z,w,h,d,mat,parent=scene) {return mesh(new THREE.BoxGeometry(w,h,d),mat,x,y,z,parent);}
    function line(points,color=0x56bfc9,opacity=.4,parent=scene) {const obj=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p))),new THREE.LineBasicMaterial({color,transparent:true,opacity}));parent.add(obj);return obj;}
    function label(text,x,y,z,width=9) {
      const c=document.createElement('canvas'); c.width=768;c.height=96;
      const ctx=c.getContext('2d');ctx.font='28px sans-serif';ctx.fillStyle='#c0eaf0';ctx.textAlign='center';ctx.fillText(text,384,58);
      const texture=new THREE.CanvasTexture(c);textures.push(texture);
      const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,transparent:true,depthWrite:false}));sprite.position.set(x,y,z);sprite.scale.set(width,width/8,1);scene.add(sprite);return sprite;
    }
    const riverX=z=>12.8+1.15*Math.sin(z*.34);
    const height=(x,z)=>{
      const mountain=6.2*Math.exp(-((x-8)**2/30+(z+11)**2/24))+4.8*Math.exp(-((x+7)**2/25+(z+13)**2/18));
      const ridge=.72*Math.sin(x*1.1+z*.7)+.3*Math.sin(x*2.7-z*1.4)+.12*Math.cos(x*5.1+z*3.7);
      const surface=.22+mountain*(1+ridge*.16)+.08*Math.sin(x*.6)*Math.cos(z*.4);
      const channel=Math.exp(-(((x-riverX(z))/.72)**4));
      return surface*(1-channel)-.15*channel;
    };
    const terrainGeometry=new THREE.PlaneGeometry(36,31,180,150);terrainGeometry.rotateX(-Math.PI/2);
    const pos=terrainGeometry.attributes.position, colors=[];
    for(let i=0;i<pos.count;i++){const x=pos.getX(i),z=pos.getZ(i)-6,y=height(x,z);pos.setXYZ(i,x,y,z);const rock=THREE.MathUtils.smoothstep(y,3.2,6.5),noise=.012*(Math.sin(x*7.3)*Math.cos(z*9.1)+Math.sin(x*19.1+z*4.7));const c=new THREE.Color(0x385d39).lerp(new THREE.Color(0x969a92),rock);if(Math.abs(x-riverX(z))<.95)c.lerp(new THREE.Color(0x8b9185),.6);c.offsetHSL(0,0,noise);colors.push(c.r,c.g,c.b);}
    terrainGeometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));terrainGeometry.computeVertexNormals();
    mesh(terrainGeometry,material(0xffffff,{vertexColors:true}));
    const waterGeo=new THREE.PlaneGeometry(1,31,8,160);waterGeo.rotateX(-Math.PI/2);
    const wp=waterGeo.attributes.position;
    for(let i=0;i<wp.count;i++){const z=wp.getZ(i)-6;wp.setXYZ(i,riverX(z)+wp.getX(i)*1.15,.025,z);}waterGeo.computeVertexNormals();
    const water=mesh(waterGeo,material(0x268d9d,{metalness:.65,roughness:.18,transparent:true,opacity:.85}));
    const ripples=[];
    for(let i=0;i<30;i++){const z=-20+i*.95;const ripple=line([[-.18,0,0],[0,.004,.025],[.18,0,0]],0xb6e8ed,.35);ripples.push({ripple,z});}
    box(0,-.55,-6,36,1,31,material(0x243039));
    const grid = new THREE.GridHelper(100,50,0x245763,0x132d34);grid.position.y=-1.1;scene.add(grid);
    const buildingMat=material(0x9cb7bb,{metalness:.25});
    const asphalt=material(0x30383d), concrete=material(0x9c9e97), roofMat=material(0x525f66), glass=material(0x284758,{metalness:.6,roughness:.23});
    for(const z of [-3.8,-.65,2.45]) {
      box(-3,.39,z,23,.06,.42,asphalt);
      for(let x=-14;x<9;x+=.8)box(x,.425,z,.3,.009,.018,white);
    }
    for(const x of [-13,-4.35,4.2])box(x,.4,.25,.38,.06,8,asphalt);
    for(let i=0;i<55;i++){const x=-12+(i%11)*1.7,z=-3+Math.floor(i/11)*1.55;
      if(x>-.5&&x<3.5&&z>-.5)continue;
      const type=i%5,h=type===0?.55:type===1?.7:type===2?2.5:.9+((i*17)%6)*.22;
      const ground=height(x,z), facade=i%3===0?concrete:buildingMat;
      box(x,ground+h/2,z,.85,h,.8,facade);
      box(x,ground+h+.035,z,.92,.07,.87,roofMat);
      box(x+.18,ground+h+.12,z-.1,.2,.17,.25,concrete);
      if(type===0){const roof=mesh(new THREE.CylinderGeometry(0,.72,.42,4),material(0x82574d),x,ground+h+.2,z);roof.rotation.y=Math.PI/4;roof.scale.z=.9;}
      if(type===1){box(x,ground+.48,z+.47,1.05,.08,.3,material(0xb58b4c));box(x,ground+.23,z+.415,.64,.32,.02,glass);}
      if(type===2){box(x,ground+h*.6,z,.92,.07,.87,white);box(x,ground+h*.3,z,.92,.07,.87,white);}
      for(let level=.3;level<h-.1;level+=.28)for(const dx of [-.25,0,.25])box(x+dx,ground+level,z+.406,.13,.15,.018,glass);
    }
    const parkGrass=material(0x446d40),pathMat=material(0xb2aba0),bark=material(0x55483a),leaf=material(0x326a42);
    const hutX=-6,hutZ=-9;
    const hutY=Math.max(...[-.65,.65].flatMap(dx=>[-.5,.65].map(dz=>height(hutX+dx,hutZ+dz))))+.08;
    const hut=new THREE.Group();hut.name='mountain-hut';hut.position.set(hutX,hutY,hutZ);scene.add(hut);
    const timberCanvas=document.createElement('canvas');timberCanvas.width=512;timberCanvas.height=256;
    const timberContext=timberCanvas.getContext('2d');timberContext.fillStyle='#89613e';timberContext.fillRect(0,0,512,256);
    for(let i=0;i<160;i++){timberContext.strokeStyle=i%3?'#68462b55':'#c79a6666';timberContext.lineWidth=.5+i%2;timberContext.beginPath();for(let x=0;x<=512;x+=8){const y=i*1.6+2*Math.sin(x*.035+i)+Math.sin(x*.087+i*.4);x?timberContext.lineTo(x,y):timberContext.moveTo(x,y);}timberContext.stroke();}
    const timberTexture=new THREE.CanvasTexture(timberCanvas);timberTexture.colorSpace=THREE.SRGBColorSpace;timberTexture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());textures.push(timberTexture);
    const timber=material(0xffffff,{map:timberTexture,roughness:.88}),darkTimber=material(0x4c3829,{roughness:.95});
    box(0,.035,.08,1.6,.07,1.45,darkTimber,hut);
    for(let row=0;row<8;row++){const y=.12+row*.09;
      for(const z of [-.48,.48])box(0,y,z,1.3,.083,.065,timber,hut);
      for(const x of [-.64,.64])box(x,y,0,.065,.083,.99,timber,hut);
    }
    for(const x of [-.62,.62])for(const z of [-.46,.46])box(x,.43,z,.085,.86,.085,darkTimber,hut);
    for(const side of [-1,1]){const roof=box(side*.39,.97,0,.92,.07,1.35,roofMat,hut);roof.rotation.z=-side*.53;
      for(let j=0;j<8;j++){const strip=box(side*.39,1.01,-.59+j*.17,.93,.015,.014,concrete,hut);strip.rotation.z=-side*.53;}}
    const gable=new THREE.Shape();gable.moveTo(-.66,0);gable.lineTo(0,.39);gable.lineTo(.66,0);gable.closePath();
    mesh(new THREE.ExtrudeGeometry(gable,{depth:.04,bevelEnabled:false}),timber,0,.77,.46,hut);
    box(0,.37,.525,.24,.61,.04,darkTimber,hut);box(.075,.35,.554,.025,.025,.018,white,hut);
    for(const x of [-.4,.4]){box(x,.48,.535,.28,.31,.04,darkTimber,hut);box(x,.48,.56,.22,.25,.012,glass,hut);box(x,.48,.571,.018,.25,.018,timber,hut);box(x,.48,.571,.22,.018,.018,timber,hut);box(x,.3,.55,.34,.05,.13,timber,hut);}
    for(let i=0;i<10;i++)box(-.72+i*.16,.08,.69,.15,.025,.3,timber,hut);
    for(const x of [-.72,.72])for(const z of [-.57,.7]){const ground=height(hutX+x,hutZ+z)-hutY;box(x,ground/2,z,.09,-ground,.09,darkTimber,hut);}
    for(let i=0;i<3;i++)box(0,-.06-i*.1,.94+i*.13,.46,.09,.16,timber,hut);
    box(.44,1.07,-.25,.17,.5,.19,concrete,hut);box(.44,1.34,-.25,.23,.045,.25,roofMat,hut);
    box(1.5,.38,1.5,3.5,.1,3.1,parkGrass);
    box(1.5,.44,1.5,3.4,.025,.3,pathMat);box(1.5,.44,1.5,.3,.025,3,pathMat);
    const parkLoop=mesh(new THREE.RingGeometry(.9,1.1,64),pathMat,1.5,.455,1.5);parkLoop.rotation.x=-Math.PI/2;parkLoop.scale.set(1.35,1.05,1);
    for(const x of [.2,2.8])for(const z of [.4,2.6]){mesh(new THREE.CylinderGeometry(.04,.06,.55,6),bark,x,.7,z);mesh(new THREE.SphereGeometry(.32,10,8),leaf,x,1.12,z);box(x,.56,z+.48,.48,.07,.16,bark);}
    const cars=[],people=[],tire=material(0x1b2025);
    // One scene unit represents about ten metres; people are 0.18 units tall.
    for(let i=0;i<9;i++){const car=new THREE.Group();scene.add(car);const paint=material([0xc64f4a,0xe2e7e3,0x487994,0xd3ac50][i%4]);
      box(0,.1,0,.44,.12,.18,paint,car);box(-.025,.19,0,.23,.09,.16,glass,car);
      for(const x of [-.14,.14])for(const z of [-.095,.095]){const wheel=mesh(new THREE.CylinderGeometry(.045,.045,.025,8),tire,x,.055,z,car);wheel.rotation.x=Math.PI/2;}
      cars.push({car,lane:i%3,offset:i*3.2});
    }
    for(let i=0;i<18;i++){const person=new THREE.Group();scene.add(person);
      mesh(new THREE.SphereGeometry(.022,7,6),material(0xc3a18a),0,.165,0,person);
      box(0,.105,0,.045,.075,.028,material([0x428b9c,0xc17757,0xc5b879][i%3]),person);
      const legs=[-.012,.012].map(x=>mesh(new THREE.CylinderGeometry(.008,.008,.065,5),tire,x,.035,0,person));
      const arms=[-.032,.032].map(x=>mesh(new THREE.CylinderGeometry(.007,.007,.065,5),material(0xc3a18a),x,.105,0,person));
      person.position.set(1.5,.46,.15+(i/18)*2.7);
      people.push({person,legs,arms,target:new THREE.Vector3(1.5,.46,1.5),wait:Math.random()*4,event:'walk',speed:.09+Math.random()*.05});
    }
    // Instancing keeps the forest detailed without hundreds of draw calls.
    const forest=new THREE.InstancedMesh(new THREE.ConeGeometry(.32,.65,12),material(0x244c35),360*3);
    const trunks=new THREE.InstancedMesh(new THREE.CylinderGeometry(.028,.05,.85,7),bark,360);
    const broadleaf=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.3,2),leaf,120);
    for(const part of [forest,trunks,broadleaf]){part.castShadow=true;part.receiveShadow=true;scene.add(part);}
    const transform=new THREE.Object3D();
    for(let i=0;i<360;i++){let x=Math.sin(i*127.1)*16;const z=-5-(.5+.5*Math.sin(i*311.7))*14,s=.55+(i%7)*.1;if(Math.abs(x-riverX(z))<1.2)x-=2;if(Math.abs(x-hutX)<1.3&&Math.abs(z-hutZ)<1.4)x-=2.6;
      const y=height(x,z);transform.rotation.y=i;transform.scale.setScalar(s);transform.position.set(x,y+s*.4,z);transform.updateMatrix();trunks.setMatrixAt(i,transform.matrix);
      for(let layer=0;layer<3;layer++){transform.position.set(x,y+s*(.55+layer*.23),z);transform.scale.setScalar(s*(1-layer*.2));transform.updateMatrix();forest.setMatrixAt(i*3+layer,transform.matrix);}
      if(i<120){transform.position.set(x+.15,y+s*.68,z);transform.scale.set(s*1.2,s,s);transform.updateMatrix();broadleaf.setMatrixAt(i,transform.matrix);}
    }
    // Include the entire train, not just its origin, within the supported track.
    // Low foreground detail leaves the railway and central valley visible.
    const foreground=new THREE.Group();foreground.name='observer-foreground';scene.add(foreground);
    box(-2,.39,7.65,27,.05,.42,pathMat,foreground);
    const treeLeaves=[0x356446,0x264f40,0x788c48,0x4b784f].map(color=>material(color,{roughness:.95}));
    const crownGeometry=new THREE.SphereGeometry(1,24,18);
    const cp=crownGeometry.attributes.position;
    for(let i=0;i<cp.count;i++){const v=new THREE.Vector3().fromBufferAttribute(cp,i),r=1+.065*Math.sin(v.x*19+v.y*7)*Math.cos(v.z*17-v.y*11);cp.setXYZ(i,v.x*r,v.y*r,v.z*r);}crownGeometry.computeVertexNormals();
    function treeBranch(parent,a,b,radius){const start=new THREE.Vector3(...a),end=new THREE.Vector3(...b),delta=end.clone().sub(start);const branch=mesh(new THREE.CylinderGeometry(radius*.4,radius,delta.length(),14,3),bark,0,0,0,parent);branch.position.copy(start.add(end).multiplyScalar(.5));branch.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());}
    for(let i=0;i<18;i++){
      const x=-15+i*1.45,z=8.5+(i%3)*.17,y=height(x,z);
      const tree=new THREE.Group();tree.name=['broadleaf','cedar','ginkgo','columnar'][i%4];tree.position.set(x,y,z);tree.rotation.y=i*2.4;tree.scale.setScalar(.85+(i%3)*.1);foreground.add(tree);
      treeBranch(tree,[0,0,0],[.018,.82,0],.042);
      for(let j=0;j<5;j++){const a=j*Math.PI*2/5;treeBranch(tree,[0,.045,0],[Math.cos(a)*.12,.015,Math.sin(a)*.12],.018);}
      const type=i%4;
      if(type===1){
        for(let tier=0;tier<5;tier++){const h=.32+tier*.145,r=.32-tier*.047;
          for(let j=0;j<7;j++){const a=j*Math.PI*2/7+tier*.5;treeBranch(tree,[0,h,0],[Math.cos(a)*r,h-.04,Math.sin(a)*r],.011);}
          mesh(new THREE.ConeGeometry(r,.32,24,4),treeLeaves[type],0,h+.1,0,tree);
        }
      }else{
        const count=type===3?9:11;
        for(let j=0;j<count;j++){const a=j*2.4,spread=type===3?.105:type===2?.24:.23,h=type===3?.42+j*.065:.55+(j%3)*.11;
          const bx=Math.cos(a)*spread,bz=Math.sin(a)*spread;
          treeBranch(tree,[0,h*.65,0],[bx,h,bz],.012);
          const crown=mesh(crownGeometry,treeLeaves[type],bx,h+.08,bz,tree);
          crown.scale.set(type===3?.14:.21,type===2?.12:type===3?.2:.18,type===3?.14:.19);
        }
      }
      if(i%3===0){box(x,.54,8,.5,.065,.16,bark,foreground);box(x,.65,8.07,.5,.16,.035,bark,foreground);for(const dx of [-.18,.18])box(x+dx,.43,8,.035,.2,.1,roofMat,foreground);}
    }
    for(const x of [-10,-6,5,8]){
      const y=height(x,8.6);
      box(x,y+.35,8.6,1.15,.7,.75,concrete,foreground);
      const roof=mesh(new THREE.CylinderGeometry(0,.9,.35,4),roofMat,x,y+.83,8.6,foreground);roof.rotation.y=Math.PI/4;roof.scale.z=.7;
      for(const dx of [-.36,0,.36])box(x+dx,y+.38,8.982,.2,.28,.015,glass,foreground);
      box(x,y+.12,9.03,.25,.24,.015,bark,foreground);
      box(x,y+.64,9.08,1.25,.04,.25,white,foreground);
    }
    for(let x=-14;x<=10;x+=3){mesh(new THREE.CylinderGeometry(.014,.023,.85,8),roofMat,x,.8,7.38,foreground);box(x,.1+1.1,7.38,.12,.035,.12,white,foreground);}
    const aircraft=new THREE.Group();aircraft.name='observer-aircraft';scene.add(aircraft);
    const fuselage=mesh(new THREE.CapsuleGeometry(.15,1.8,10,20),white,0,0,0,aircraft);fuselage.rotation.z=Math.PI/2;
    const cockpit=mesh(new THREE.SphereGeometry(1,16,12),glass,.86,.065,0,aircraft);cockpit.scale.set(.2,.085,.135);
    function aircraftSurface(points,thickness,mat){const shape=new THREE.Shape();points.forEach(([x,z],i)=>i?shape.lineTo(x,z):shape.moveTo(x,z));shape.closePath();const geo=new THREE.ExtrudeGeometry(shape,{depth:thickness,bevelEnabled:false});geo.rotateX(Math.PI/2);return mesh(geo,mat,0,0,0,aircraft);}
    for(const side of [-1,1]){
      aircraftSurface([[.3,side*.1],[-.35,side*1.2],[-.65,side*1.2],[-.35,side*.1]],.035,white);
      aircraftSurface([[-.7,side*.1],[-1,side*.52],[-1.15,side*.52],[-1.05,side*.1]],.025,white);
      const engine=mesh(new THREE.CylinderGeometry(.09,.075,.36,16),white,-.2,-.12,side*.48,aircraft);engine.rotation.z=Math.PI/2;
      const intake=mesh(new THREE.CircleGeometry(.065,16),tire,-.012,-.12,side*.48,aircraft);intake.rotation.y=Math.PI/2;
      for(let i=0;i<10;i++)box(.6-i*.135,.035,side*.149,.04,.045,.009,glass,aircraft);
    }
    const tail=aircraftSurface([[-.65,0],[-1.04,.5],[-1.2,.5],[-1.04,0]],.035,teal);tail.rotation.x=-Math.PI/2;
    let flightDirection=Math.random()<.5?-1:1,flightWait=0,flightSpeed=1.5+Math.random()*.6;
    aircraft.position.set(-flightDirection*40,16,-15);aircraft.rotation.y=flightDirection>0?0:Math.PI;
    const railZ=5.8,trainTravelLimit=26,trainExtent=7.7,railHalfLength=trainTravelLimit+trainExtent+3;
    box(0,1,railZ,railHalfLength*2,.2,.7,material(0x657d83));
    for(const dz of [-.23,.23])box(0,1.15,railZ+dz,railHalfLength*2,.045,.045,white);
    for(let x=-railHalfLength;x<=railHalfLength;x+=2)box(x,0,railZ,.18,2.1,.35,buildingMat);
    for(let x=-railHalfLength;x<=railHalfLength;x+=.35)box(x,1.12,railZ,.08,.05,.65,roofMat);
    for(const dz of [-.4,.4])box(0,1.32,railZ+dz,railHalfLength*2,.12,.045,concrete);
    const train = new THREE.Group();train.name='observer-train';scene.add(train);train.position.z=railZ;
    for(let i=0;i<4;i++){
      const body=mesh(new THREE.CapsuleGeometry(.22,1.45,8,16),white,i*2,1.47,0,train);body.rotation.z=Math.PI/2;body.scale.z=.72;
      for(const side of [-1,1]){box(i*2,1.43,side*.161,1.8,.035,.014,teal,train);
        for(let j=0;j<8;j++)box(i*2-.7+j*.2,1.52,side*.163,.125,.105,.012,glass,train);}
      for(const x of [-.6,.6]){box(i*2+x,1.24,0,.27,.09,.24,tire,train);}
      if(i<3)box(i*2+1,1.42,0,.16,.2,.2,roofMat,train);
    }
    for(const x of [-1.05,7.05]){const nose=mesh(new THREE.SphereGeometry(1,24,16),white,x,1.43,0,train);nose.scale.set(.64,.19,.16);const windscreen=mesh(new THREE.SphereGeometry(1,16,12),glass,x,1.52,0,train);windscreen.scale.set(.22,.1,.145);}
    let trainDirection=Math.random()<.5?-1:1,trainWait=0;
    train.position.x=trainDirection>0?-25:25;train.rotation.y=trainDirection>0?0:Math.PI;
    const boats=[];
    for(let i=0;i<2;i++){
      const boat=new THREE.Group();boat.name='observer-boat';scene.add(boat);
      const hullShape=new THREE.Shape();hullShape.moveTo(0,.48);hullShape.bezierCurveTo(.15,.34,.16,-.2,.11,-.4);hullShape.lineTo(-.11,-.4);hullShape.bezierCurveTo(-.16,-.2,-.15,.34,0,.48);
      const hullGeo=new THREE.ExtrudeGeometry(hullShape,{depth:.1,bevelEnabled:true,bevelThickness:.018,bevelSize:.018,bevelSegments:3,steps:1});hullGeo.rotateX(Math.PI/2);
      mesh(hullGeo,material(i?0x345c79:0xe3ded0),0,.075,0,boat);
      box(0,.087,-.03,.22,.018,.57,material(0xb7a58a),boat);
      box(0,.18,-.055,.18,.16,.29,white,boat);
      for(const side of [-1,1])for(let j=0;j<3;j++)box(side*.093,.207,-.14+j*.08,.009,.065,.055,glass,boat);
      box(0,.208,.095,.15,.068,.012,glass,boat);
      box(0,.27,-.055,.22,.025,.34,white,boat);
      mesh(new THREE.CylinderGeometry(.006,.006,.22,8),white,0,.39,-.08,boat);
      box(0,.48,-.08,.11,.01,.012,white,boat);
      for(const side of [-1,1]){
        for(let j=0;j<5;j++)mesh(new THREE.CylinderGeometry(.004,.004,.07,6),white,side*.116,.13,-.31+j*.12,boat);
        line([[side*.116,.168,-.31],[side*.116,.168,.2],[side*.06,.168,.35]],0xe5edef,.9,boat);
      }
      const buoy=mesh(new THREE.TorusGeometry(.035,.011,8,16),material(0xe47b36),.108,.18,-.07,boat);buoy.rotation.y=Math.PI/2;
      const wake=new THREE.Group();scene.add(wake);
      for(const side of [-1,1])line([[side*.06,.033,-.35],[side*.16,.033,-.65],[side*.25,.033,-1]],0xc9f3ef,.3,wake);
      const direction=i?1:-1;
      boats.push({boat,wake,direction,z:i?-13:3,speed:.2+Math.random()*.12,wait:0});
    }
    const drones=[];
    for(let i=0;i<3;i++){const drone=new THREE.Group();scene.add(drone);const shell=mesh(new THREE.SphereGeometry(1,20,12),white,0,0,0,drone);shell.scale.set(.18,.08,.22);
      const rotors=[];
      for(const x of [-.3,.3])for(const z of [-.3,.3]){box(x/2,0,z/2,.43,.03,.03,roofMat,drone).rotation.y=x*z>0?-.8:.8;mesh(new THREE.CylinderGeometry(.035,.035,.08,12),tire,x,.025,z,drone);const rotor=new THREE.Group();rotor.position.set(x,.08,z);drone.add(rotor);box(0,0,0,.34,.01,.035,roofMat,rotor);rotors.push(rotor);}
      for(const x of [-.12,.12]){box(x,-.13,0,.015,.18,.015,roofMat,drone);box(x,-.22,0,.025,.015,.3,roofMat,drone);}
      mesh(new THREE.SphereGeometry(.045,12,8),tire,0,-.105,.12,drone);
      drone.scale.setScalar(.65);drones.push({drone,rotors});}
    const stations=[[-10,-5],[8,1],[1,-10]], rings=[];
    stations.forEach(([x,z])=>{const y=height(x,z);mesh(new THREE.CylinderGeometry(.055,.12,2.5,8),white,x,y+1.25,z);box(x,y+2.5,z,.55,.65,.22,teal);
      for(const dx of [-.18,.18]){
        mesh(new THREE.CylinderGeometry(.024,.04,2.7,6),roofMat,x+dx,y+1.35,z+.15);
        for(let k=0;k<5;k++)line([[x-.18,y+k*.5,z+.15],[x+.18,y+(k+1)*.5,z+.15]],0xa7b5bc,.8);
      }
      for(let k=0;k<3;k++){const a=k*Math.PI*2/3;const antenna=box(x+Math.cos(a)*.24,y+2.65,z+Math.sin(a)*.24,.16,.7,.1,white);antenna.rotation.y=-a;}
      for(let j=0;j<4;j++){const ring=mesh(new THREE.RingGeometry(.97,1,100),new THREE.MeshBasicMaterial({color:0x36caff,transparent:true,opacity:.5,side:THREE.DoubleSide,depthWrite:false,blending:THREE.AdditiveBlending}),x,y+2.65,z);ring.rotation.x=-Math.PI/2;rings.push({ring,phase:j/4,altitude:y+2.65});}
    });
    const heatGeo=new THREE.PlaneGeometry(29,22,65,50);heatGeo.rotateX(-Math.PI/2);
    const hp=heatGeo.attributes.position,hc=[];
    const fieldHeight=(x,z)=>4.1+height(x,z)*.65;
    const strengthAt=(x,z)=>Math.max(...stations.map(([sx,sz])=>Math.exp(-((x-sx)**2+(z-sz)**2)/23)));
    for(let i=0;i<hp.count;i++){const x=hp.getX(i),z=hp.getZ(i)-4;hp.setXYZ(i,x,fieldHeight(x,z),z);const strength=strengthAt(x,z);const c=new THREE.Color().setHSL((1-strength)*.65,1,.52);hc.push(c.r,c.g,c.b);}
    heatGeo.setAttribute('color',new THREE.Float32BufferAttribute(hc,3));heatGeo.computeVertexNormals();
    const heat=mesh(heatGeo,new THREE.MeshBasicMaterial({vertexColors:true,transparent:true,opacity:.4,side:THREE.DoubleSide,depthWrite:false}));
    const contours=new THREE.Group();scene.add(contours);
    for(const [sx,sz] of stations)for(const level of [.3,.55,.8]){
      const r=Math.sqrt(-23*Math.log(level)),points=[];
      for(let i=0;i<=100;i++){const a=i/100*Math.PI*2,x=sx+r*Math.cos(a),z=sz+r*Math.sin(a);
        if(Math.abs(x)<=14.5&&z>=-15&&z<=7&&strengthAt(x,z)<level+.015)points.push([x,fieldHeight(x,z)+.025,z]);
        else {if(points.length>1)line(points,0xdcf6ff,.35,contours);points.length=0;}}
      if(points.length>1)line(points,0xdcf6ff,.35,contours);
    }
    dialog.querySelector('#observer-heat').onchange=event=>{heat.visible=contours.visible=event.target.checked;};
    dialog.querySelector('#observer-opacity').oninput=event=>{const value=Number(event.target.value);heat.material.opacity=value/100;contours.children.forEach(child=>child.material.opacity=value/100*.875);dialog.querySelector('output').textContent=value+'%';};
    const observerOrigin=new THREE.Vector3(0,7.5,17.5);
    const aroundObserver=(angle,r,y)=>new THREE.Vector3(observerOrigin.x+Math.sin(angle)*r,y,observerOrigin.z-Math.cos(angle)*r);
    function curvedTitle(text,angle,r,y,width) {
      const canvas=document.createElement('canvas');canvas.width=1536;canvas.height=128;
      const context=canvas.getContext('2d');context.font='42px sans-serif';context.textAlign='center';context.fillStyle='#c0eaf0';context.fillText(text,768,80);
      const texture=new THREE.CanvasTexture(canvas);textures.push(texture);
      const geo=new THREE.PlaneGeometry(width,width/12,64,1),positions=geo.attributes.position;
      for(let i=0;i<positions.count;i++){const point=aroundObserver(angle+positions.getX(i)/r,r,y+positions.getY(i));positions.setXYZ(i,point.x,point.y,point.z);}geo.computeVertexNormals();
      mesh(geo,new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false,side:THREE.DoubleSide}));
    }
    const modelViewingRadius=34;
    const nodes=[],edges=[],layerSizes=[7,10,12,10,6];
    layerSizes.forEach((count,l)=>{for(let i=0;i<count;i++){
      const angle=-.76+l*.105,r=modelViewingRadius-Math.floor(i/4)*1.9,y=4.4+(i%4)*1.7,point=aroundObserver(angle,r,y);
      const node=mesh(new THREE.SphereGeometry(.24,16,12),material(0x287c90,{emissive:0x31d9ef,emissiveIntensity:.08}),point.x,point.y,point.z);nodes.push({node,l,i,angle,r});
      if(l>0)for(const prev of nodes.filter(n=>n.l===l-1 && (n.i+i)%3===0))edges.push(line(Array.from({length:13},(_,j)=>{const u=j/12;return aroundObserver(THREE.MathUtils.lerp(prev.angle,angle,u),THREE.MathUtils.lerp(prev.r,r,u),THREE.MathUtils.lerp(prev.node.position.y,y,u)).toArray();}),0x32bad7,.12));
    }});
    curvedTitle('NEURAL ENSEMBLE',-.55,modelViewingRadius,10.8,11);
    const outputGeo=new THREE.PlaneGeometry(8,8,40,40);outputGeo.rotateX(-Math.PI/2);
    const op=outputGeo.attributes.position, base=Float32Array.from(op.array);
    const outputAngle=.57,outputPoint=aroundObserver(outputAngle,modelViewingRadius,5);
    const output=mesh(outputGeo,new THREE.MeshPhysicalMaterial({color:0x59e6cc,metalness:.25,roughness:.3,transparent:true,opacity:.55,side:THREE.DoubleSide,wireframe:true,emissive:0x087c75,emissiveIntensity:.5}),outputPoint.x,outputPoint.y,outputPoint.z);
    output.rotation.order='YXZ';output.rotation.set(.65,-outputAngle,0);
    curvedTitle('RSS MODEL / TRAINING STATE',outputAngle,modelViewingRadius,10.8,11);
    const arc=Math.PI*100/180,radius=23,screenHeight=12,screenBottom=6,screenTop=screenBottom+screenHeight,screenWidth=radius*arc;
    const logCanvas=document.createElement('canvas');logCanvas.width=3072;logCanvas.height=Math.round(logCanvas.width*screenHeight/screenWidth);
    const ctx=logCanvas.getContext('2d'), logTexture=new THREE.CanvasTexture(logCanvas);textures.push(logTexture);
    // The screen wraps around the fixed observer rather than following the mouse.
    const screenGeo=new THREE.PlaneGeometry(screenWidth,screenHeight,80,1);
    const sp=screenGeo.attributes.position;
    for(let i=0;i<sp.count;i++){const angle=sp.getX(i)/radius;sp.setXYZ(i,Math.sin(angle)*radius,sp.getY(i)+screenBottom+screenHeight/2,17.5-Math.cos(angle)*radius);}screenGeo.computeVertexNormals();
    mesh(screenGeo,new THREE.MeshBasicMaterial({map:logTexture,transparent:true,depthWrite:false,side:THREE.DoubleSide}));
    for(const y of [screenBottom,screenTop])line(Array.from({length:81},(_,i)=>{const a=-arc/2+arc*i/80;return [Math.sin(a)*radius,y,17.5-Math.cos(a)*radius];}),0x54d7ff,.45);
    for(const a of [-arc/2,arc/2])line([[Math.sin(a)*radius,screenBottom,17.5-Math.cos(a)*radius],[Math.sin(a)*radius,screenTop,17.5-Math.cos(a)*radius]],0x54d7ff,.45);
    function paintLog(text,t) {
      const scale=logCanvas.width/2560;
      ctx.setTransform(scale,0,0,scale,0,0);
      const w=logCanvas.width/scale,h=logCanvas.height/scale,columnWidth=w/3;
      // Keep live text in the readable central band as the glass extends upward.
      const headerY=(screenTop-14.1)*2560/screenWidth;
      ctx.clearRect(0,0,w,h);ctx.fillStyle='rgba(6,28,39,.08)';ctx.fillRect(0,0,w,h);
      ctx.fillStyle='#93eaff';ctx.font='24px monospace';ctx.fillText('APPLICATION LOG / LIVE',columnWidth+30,headerY);
      ctx.save();ctx.beginPath();ctx.rect(20,headerY+20,w-40,h-headerY-35);ctx.clip();ctx.font='22px monospace';
      const count=Math.floor((h-headerY-55)/30),lines=text.split('\n').flatMap(s=>s.match(/.{1,56}/g)||['']).slice(-count*3);
      const slide=30*(1-Math.min(1,(t-logChangedAt)/.35));
      const columns=[lines.slice(-count*2,-count),lines.slice(-count),lines.slice(0,Math.max(0,lines.length-count*2))];
      columns.forEach((rows,column)=>rows.forEach((s,i)=>{ctx.fillStyle=column===1?'#d2fff4':'#81b9cb';ctx.fillText(s,30+column*columnWidth,headerY+50+i*30+slide);}));ctx.restore();logTexture.needsUpdate=true;
    }
    let yaw=0,pitch=0,targetYaw=0,targetPitch=0, previousTime=0, checkAt=-1, state='Idle', progress=0;
    const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
    const start=performance.now();
    // Aircraft-local +X is forward. The swept wing trails toward -X in both directions.
    const cabinWing=new THREE.Group();cabinWing.name='passenger-wing';scene.add(cabinWing);cabinWing.visible=false;
    const reflectionCanvas=document.createElement('canvas');reflectionCanvas.width=512;reflectionCanvas.height=256;
    const reflectionContext=reflectionCanvas.getContext('2d'),sky=reflectionContext.createLinearGradient(0,0,0,256);
    sky.addColorStop(0,'#537896');sky.addColorStop(.45,'#e3eff5');sky.addColorStop(.52,'#adbcc2');sky.addColorStop(1,'#364447');reflectionContext.fillStyle=sky;reflectionContext.fillRect(0,0,512,256);
    const reflection=new THREE.CanvasTexture(reflectionCanvas);reflection.mapping=THREE.EquirectangularReflectionMapping;reflection.colorSpace=THREE.SRGBColorSpace;textures.push(reflection);
    const aluminum=material(0xaab7c2,{metalness:.88,roughness:.27,envMap:reflection,envMapIntensity:1.1});
    const leadingMetal=material(0xd2dae0,{metalness:.95,roughness:.18,envMap:reflection,envMapIntensity:1.2});
    const outline=new THREE.Shape();outline.moveTo(.4,.08);outline.lineTo(-.42,1.55);outline.lineTo(-.72,1.72);outline.lineTo(-.9,1.65);outline.lineTo(-.53,.08);outline.closePath();
    const wingGeo=new THREE.ExtrudeGeometry(outline,{depth:.035,bevelEnabled:true,bevelThickness:.012,bevelSize:.012,bevelSegments:3});wingGeo.rotateX(Math.PI/2);
    mesh(wingGeo,aluminum,0,-.035,0,cabinWing);
    const leadingPath=new THREE.CatmullRomCurve3([new THREE.Vector3(.4,-.035,.08),new THREE.Vector3(-.42,-.035,1.55),new THREE.Vector3(-.72,-.035,1.72)]);
    mesh(new THREE.TubeGeometry(leadingPath,32,.013,10,false),leadingMetal,0,0,0,cabinWing);
    for(let i=0;i<6;i++){const z=.25+i*.22,front=.4-(z-.08)*.558,back=-.53-(z-.08)*.235;
      line([[front,-.02,z],[back,-.02,z]],0x52616a,.7,cabinWing);
      for(let j=0;j<5;j++)mesh(new THREE.SphereGeometry(.0035,5,4),leadingMetal,THREE.MathUtils.lerp(front,back,j/4),-.016,z,cabinWing);
    }
    line([[-.35,-.02,.14],[-.69,-.02,1.42]],0x45535e,.85,cabinWing);
    for(const z of [.5,.95]){const fairing=mesh(new THREE.SphereGeometry(1,16,10),aluminum,-.5,-.095,z,cabinWing);fairing.scale.set(.23,.055,.045);}
    const wingRoot=mesh(new THREE.SphereGeometry(1,32,20),aluminum,-.06,-.07,.06,cabinWing);
    wingRoot.scale.set(.62,.09,.27);
    const fuselageSection=mesh(new THREE.CapsuleGeometry(.18,1.9,10,24),aluminum,0,-.13,-.12,cabinWing);
    fuselageSection.rotation.z=Math.PI/2;
    let cameraMode='overview',cameraTransition=null,cabinOpacity=0;
    const cabin=dialog.querySelector('.observer-cabin');
    const canBoardTrain=()=>trainWait<=0&&train.visible&&Math.abs(train.position.x)<16;
    const canBoardAircraft=()=>flightWait<=0&&aircraft.visible&&Math.abs(aircraft.position.x)<17;
    let selectedBoat=null;
    const availableBoat=()=>boats.find(v=>v.wait<=0&&v.boat.visible&&v.z> -15&&v.z<6);
    function switchCamera(toTrain,toPlane=false,toBoat=false) {
      if(cameraTransition)return;
      if(toPlane&&!canBoardAircraft())return;
      if(toBoat){const vessel=availableBoat();if(!vessel)return;selectedBoat=vessel;}
      if(toTrain){
        if(!canBoardTrain())return;
        cabin.classList.toggle('reverse-direction',trainDirection>0);
        cabin.dataset.travelDirection=trainDirection>0?'left-to-right':'right-to-left';
        dialog.classList.add('train-view');
      }
      if(toPlane||toBoat){dialog.classList.add('train-view');}
      cameraMode=toTrain||toPlane||toBoat?'boarding':'returning';dialog.dataset.cameraMode=cameraMode;
      cameraTransition={toTrain,toPlane,toBoat,start:performance.now(),position:camera.position.clone(),quaternion:camera.quaternion.clone(),opacity:cabinOpacity,fov:camera.fov};
      targetYaw=targetPitch=0;rideButton.disabled=true;
      rideButton.setAttribute('aria-pressed',String(toTrain));
      const text=toTrain?'Return to observatory':'Train window view';rideButton.title=text;rideButton.setAttribute('aria-label',text);
      flightButton.setAttribute('aria-pressed',String(toPlane));flightButton.setAttribute('aria-label',toPlane?'Return from aircraft':'Aircraft window view');flightButton.title=toPlane?'Return to observatory':'Aircraft window view';
      boatButton.setAttribute('aria-pressed',String(toBoat));boatButton.setAttribute('aria-label',toBoat?'Return from boat':'Boat view');boatButton.title=toBoat?'Return to observatory':'Boat view';
      dialog.querySelector('.observer-hud h2').textContent=toBoat?'Boat View':toPlane?'Aircraft Window View':toTrain?'Train Window View':'Neural Training Observatory';
      dialog.querySelector('.observer-hud p').textContent=toBoat?'Forward deck · River journey':toPlane?'Wing-side seat · Scenic flight':toTrain?'Window seat · Scenic rail journey':'Illustrative digital twin · Live application log';
    }
    rideButton.onclick=()=>switchCamera(cameraMode==='overview');
    flightButton.onclick=()=>switchCamera(false,cameraMode==='overview');
    boatButton.onclick=()=>switchCamera(false,false,cameraMode==='overview');
    const lookLimits=()=>cameraMode==='boat'?{yaw:Math.PI/4,pitch:Math.PI/9}:{yaw:.2095,pitch:.1045};
    renderer.domElement.addEventListener('pointermove',event=>{const limits=lookLimits();targetYaw=-(event.clientX/dialog.clientWidth-.5)*limits.yaw*2;targetPitch=-(event.clientY/dialog.clientHeight-.5)*limits.pitch*2;});
    renderer.domElement.addEventListener('pointerleave',()=>{targetYaw=0;targetPitch=0;});
    dialog.addEventListener('keydown',event=>{if(event.target.matches('input'))return;if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();const limits=lookLimits();targetYaw=THREE.MathUtils.clamp(targetYaw+(event.key==='ArrowLeft'?.03:event.key==='ArrowRight'?-.03:0),-limits.yaw,limits.yaw);targetPitch=THREE.MathUtils.clamp(targetPitch+(event.key==='ArrowUp'?.02:event.key==='ArrowDown'?-.02:0),-limits.pitch,limits.pitch);}if(event.key==='Home'){targetYaw=0;targetPitch=0;}});
    renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();dialog.querySelector('.observer-status').textContent='Graphics paused. Exit and reopen this view.';cancelAnimationFrame(frame);});
    function animate(now) {
      frame=requestAnimationFrame(animate);
      if(document.hidden)return;
      const t=Math.max(0,(now-start)/1000),dt=Math.max(0,Math.min(.05,t-previousTime));previousTime=t;
      if(t-checkAt>.2){checkAt=t;state=document.getElementById('training-visual-state')?.textContent||'Idle';
        progress=state==='Complete'?1:state==='Training'?Math.max(0,Math.min(1,parseFloat(document.getElementById('runtime-pill')?.textContent)/100||0)):0;
        const terminal=document.getElementById('terminal-content-main');
        const text=terminal?.children.length?Array.from(terminal.children).slice(-20).map(row=>row.textContent).join('\n'):terminal?.textContent||'Waiting for system activity.';
        if(text!==lastLog){lastLog=text;logChangedAt=t;}paintLog(lastLog,t);
        dialog.querySelector('.observer-status').textContent=`${state}${state==='Training'?' · '+Math.round(progress*100)+'%':''} · Fixed observation`;
        for(let i=0;i<op.count;i++){const step=1.4-progress*1.3,x=Math.round(base[i*3]/step)*step,z=Math.round(base[i*3+2]/step)*step;op.setXYZ(i,x,.3+(1+progress*2)*Math.exp(-(x*x+z*z)/10)+progress*.35*Math.sin(x*3)*Math.cos(z*2),z);}op.needsUpdate=true;outputGeo.computeVertexNormals();
      }
      const u=reduce?1:Math.min(1,t/2.2),ease=u*u*(3-2*u);
      camera.position.set(0,21+(7.5-21)*ease,37+(17.5-37)*ease);
      yaw+=(targetYaw-yaw)*(1-Math.exp(-dt*4));pitch+=(targetPitch-pitch)*(1-Math.exp(-dt*4));
      camera.rotation.order='YXZ';camera.rotation.set(-.20+pitch*ease,yaw*ease,0);
      const motion=reduce?0:t;
      const step=reduce?0:dt;
      if(flightWait>0){flightWait-=step;aircraft.visible=false;}else{
        aircraft.visible=true;aircraft.position.x+=flightDirection*flightSpeed*step;
        if(Math.abs(aircraft.position.x)>40){flightDirection=Math.random()<.5?-1:1;aircraft.position.set(-flightDirection*40,14+Math.random()*3,-12-Math.random()*8);aircraft.rotation.y=flightDirection>0?0:Math.PI;flightSpeed=1.5+Math.random()*.6;flightWait=8+Math.random()*16;aircraft.visible=false;}
      }
      if(trainWait>0){trainWait-=step;train.visible=false;}else{train.visible=true;train.position.x+=trainDirection*step*1.8;
        if(Math.abs(train.position.x)>trainTravelLimit){trainDirection=Math.random()<.5?-1:1;train.position.x=trainDirection>0?-25:25;train.rotation.y=trainDirection>0?0:Math.PI;trainWait=2+Math.random()*5;}}
      boats.forEach(vessel=>{
        const {boat,wake}=vessel;
        if(vessel.wait>0){vessel.wait-=step;boat.visible=wake.visible=false;return;}
        vessel.z+=vessel.direction*vessel.speed*step;
        if(vessel.z>8.8||vessel.z< -20.8){vessel.direction=Math.random()<.5?-1:1;vessel.z=vessel.direction>0?-20.8:8.8;vessel.speed=.2+Math.random()*.12;vessel.wait=3+Math.random()*8;boat.visible=wake.visible=false;return;}
        boat.visible=wake.visible=true;
        const tangent=.391*Math.cos(vessel.z*.34),heading=Math.atan2(tangent*vessel.direction,vessel.direction);
        boat.position.set(riverX(vessel.z)+vessel.direction*.2,.025+Math.sin(motion*1.8+vessel.z)*.007,vessel.z);
        boat.rotation.set(0,heading,Math.sin(motion*1.5+vessel.z)*.018);
        wake.position.set(boat.position.x,0,vessel.z);wake.rotation.y=heading;
      });
      cars.forEach(({car,lane,offset})=>car.position.set(-14+(motion*.55+offset)%23,.43,[-3.8,-.65,2.45][lane]));
      people.forEach(actor=>{const {person,legs,arms,target}=actor;let walking=false;
        if(actor.wait>0){actor.wait-=step;}else if(person.position.distanceTo(target)>.025){walking=true;const dx=target.x-person.position.x,dz=target.z-person.position.z,len=Math.hypot(dx,dz),travel=Math.min(len,step*actor.speed);person.position.x+=dx/len*travel;person.position.z+=dz/len*travel;person.rotation.y=Math.atan2(dx,dz);}
        else{actor.wait=2+Math.random()*6;actor.event=Math.random()<.3?'wave':'rest';const atCenter=Math.abs(person.position.x-1.5)<.03&&Math.abs(person.position.z-1.5)<.03;
          if(atCenter){const endpoints=[[.15,1.5],[2.85,1.5],[1.5,.15],[1.5,2.85]];const [x,z]=endpoints[Math.floor(Math.random()*endpoints.length)];target.set(x,.46,z);}else target.set(1.5,.46,1.5);}
        legs.forEach((leg,i)=>leg.rotation.x=walking?Math.sin(motion*5+i*Math.PI)*.35:0);arms.forEach((arm,i)=>arm.rotation.z=!walking&&actor.event==='wave'&&i===0?-1.8+Math.sin(motion*4)*.2:0);
      });
      drones.forEach(({drone,rotors},i)=>{drone.position.set(Math.sin(motion*.22+i*2)*9,5+i*.7+Math.sin(motion+i)*.25,Math.cos(motion*.22+i*2)*5-3);drone.rotation.z=Math.sin(motion*.22+i)*.08;rotors.forEach(rotor=>rotor.rotation.y=motion*35);});
      ripples.forEach(({ripple,z},i)=>{const rz=z+(motion*.15)% .95;ripple.position.set(riverX(rz),.035,rz);ripple.material.opacity=.15+.15*Math.sin(motion*2+i);});
      rings.forEach(({ring,phase,altitude})=>{const p=(motion*.23+phase)%1;ring.scale.setScalar(.4+p*6);ring.position.y=altitude+p*.8;ring.material.opacity=(1-p)*.65;});
      nodes.forEach(({node,l,i})=>{const active=state==='Training'&&Math.sin(motion*3-l*.9+i*.4)>.3;node.material.emissiveIntensity=state==='Complete'?.6:active?2:.08;});
      edges.forEach((edge,i)=>edge.material.opacity=state==='Training'?.12+.23*(.5+.5*Math.sin(motion*3-i)):.12);
      if(cameraMode!=='overview'){
        const toTrain=cameraTransition?cameraTransition.toTrain:cameraMode==='train';
        const toPlane=cameraTransition?cameraTransition.toPlane:cameraMode==='flight';
        const toBoat=cameraTransition?cameraTransition.toBoat:cameraMode==='boat';
        const deckOffset=toBoat?new THREE.Vector3(0,.3,.15).applyAxisAngle(new THREE.Vector3(0,1,0),selectedBoat.boat.rotation.y):null;
        const targetPosition=toBoat?selectedBoat.boat.position.clone().add(deckOffset):toPlane?aircraft.position.clone().add(new THREE.Vector3(flightDirection*.65,.65,.05)):toTrain?new THREE.Vector3(train.position.x+trainDirection*2,1.54,railZ):new THREE.Vector3(0,7.5,17.5);
        // Look along travel through the side window; the cabin mirrors separately.
        const targetRotation=new THREE.Quaternion().setFromEuler(new THREE.Euler(toBoat?-.08+pitch*.65:toPlane?-.95+pitch*.7:toTrain?-.035+pitch*.65:-.2+pitch,toBoat?selectedBoat.boat.rotation.y+Math.PI+yaw:toPlane?Math.PI-flightDirection*.22+yaw*.7:toTrain?-trainDirection*.5+yaw*.9:yaw,0,'YXZ'));
        const targetFov=toBoat?88:toPlane?76:toTrain?(camera.aspect<1?90:82):(camera.aspect<1?85:62);
        if(cameraTransition){
          const fraction=reduce?1:Math.min(1,(now-cameraTransition.start)/1900),blend=Math.max(0,fraction*fraction*(3-2*fraction));
          camera.position.lerpVectors(cameraTransition.position,targetPosition,blend);camera.quaternion.slerpQuaternions(cameraTransition.quaternion,targetRotation,blend);
          cabinOpacity=THREE.MathUtils.lerp(cameraTransition.opacity,toTrain?1:0,blend);
          camera.fov=THREE.MathUtils.lerp(cameraTransition.fov,targetFov,blend);camera.updateProjectionMatrix();
          if(fraction>=1){cameraMode=toBoat?'boat':toPlane?'flight':toTrain?'train':'overview';dialog.dataset.cameraMode=cameraMode;cameraTransition=null;rideButton.disabled=false;if(!toTrain&&!toPlane&&!toBoat)dialog.classList.remove('train-view');}
        }else{camera.position.copy(targetPosition);camera.quaternion.copy(targetRotation);camera.fov=targetFov;camera.updateProjectionMatrix();}
        cabin.style.opacity=String(cabinOpacity);
        // Hide the exterior shell while seated inside its window.
        if(toTrain)train.visible=false;
        if(toPlane)aircraft.visible=false;
        cabinWing.visible=toPlane&&!cameraTransition;
        cabinWing.position.copy(aircraft.position);cabinWing.rotation.y=aircraft.rotation.y;cabinWing.scale.set(.75,.75,.75*flightDirection);
        if(cameraMode==='flight'&&Math.abs(aircraft.position.x)>22)switchCamera(false);
        if(cameraMode==='train'&&Math.abs(train.position.x)>18)switchCamera(false);
        if(cameraMode==='boat'&&(selectedBoat.z>8||selectedBoat.z< -20))switchCamera(false);
      }
      if(cameraMode==='overview')cabinWing.visible=false;
      rideButton.disabled=!!cameraTransition||!['overview','train'].includes(cameraMode)||(cameraMode==='overview'&&!canBoardTrain());
      flightButton.disabled=!!cameraTransition||!['overview','flight'].includes(cameraMode)||(cameraMode==='overview'&&!canBoardAircraft());
      boatButton.disabled=!!cameraTransition||!['overview','boat'].includes(cameraMode)||(cameraMode==='overview'&&!availableBoat());
      if(cameraMode==='overview')boatButton.title=boatButton.disabled?'Waiting for a passing boat':'Boat view';
      if(cameraMode==='overview')flightButton.title=flightButton.disabled?'Waiting for a passing aircraft':'Aircraft window view';
      if(cameraMode==='overview')rideButton.title=rideButton.disabled?'Waiting for a passing train':'Train window view';
      renderer.render(scene,camera);
    }
    frame=requestAnimationFrame(animate);
  }};
})();
