/* Lightweight natural setting: colored terrain, instanced vegetation and a small settlement. */
(function () {
  'use strict';
  window.ASSETNaturalEnvironment = function (T, world, heightAt, mobile) {
    let seed = 7183;
    const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const matrixObject = new T.Object3D();
    const roadSamples = [];
    const asphalt = new T.MeshStandardMaterial({ color: 0x727b7b, roughness: 0.95 });
    function road(points, width) {
      const curve = new T.CatmullRomCurve3(points.map(([x, z]) => new T.Vector3(x, 0, z)));
      const vertices = [], indices = [];
      for (let n = 0; n <= 160; n++) {
        const point = curve.getPoint(n / 160), direction = curve.getTangent(n / 160);
        roadSamples.push([point.x, point.z]);
        for (const sign of [-1, 1]) {
          const x = point.x + direction.z * width * sign / 2;
          const z = point.z - direction.x * width * sign / 2;
          vertices.push(x, heightAt(x, z) + 0.039, z);
        }
        if (n < 160) { const i = n * 2; indices.push(i, i + 2, i + 1, i + 1, i + 2, i + 3); }
      }
      const geometry = new T.BufferGeometry();
      geometry.setAttribute('position', new T.Float32BufferAttribute(vertices, 3));
      geometry.setIndex(indices); geometry.computeVertexNormals();
      const mesh = new T.Mesh(geometry, asphalt); mesh.receiveShadow = true; world.add(mesh);
      return curve;
    }
    const mainRoad = road([[-4.9, 3.65], [-2.6, 3.5], [-0.5, 3.85], [1.8, 3.7], [4.9, 3.25]], 0.5);
    road([[-3.6, 3.55], [-3.7, 2.85], [-3.4, 2.2]], 0.11);
    road([[3.6, 3.45], [3.65, 2.6], [3.15, 2.35]], 0.11);
    const lanePaint = new T.InstancedMesh(new T.BoxGeometry(0.012, 0.003, 0.12), new T.MeshBasicMaterial({ color: 0xece7cd }), 45);
    for (let n = 0; n < 45; n++) {
      const p = mainRoad.getPoint((n + 0.5) / 45), tangent = mainRoad.getTangent((n + 0.5) / 45);
      matrixObject.position.set(p.x, heightAt(p.x, p.z) + 0.047, p.z);
      matrixObject.rotation.set(0, Math.atan2(tangent.x, tangent.z), 0); matrixObject.scale.set(1, 1, 1); matrixObject.updateMatrix();
      lanePaint.setMatrixAt(n, matrixObject.matrix);
    }
    world.add(lanePaint);

    const sites = [
      [-3.9, 4.25, .42, .35, .31], [-2.95, 4.2, .48, .37, .41], [-2.15, 4.25, .38, .34, .29],
      [-1.2, 4.5, .46, .32, .36], [-.25, 4.5, .39, .38, .34], [.7, 4.4, .5, .4, .48],
      [1.8, 4.35, .4, .36, .35], [3.6, 4.15, .52, .38, .53], [4.35, 3.95, .38, .38, .34],
      [-4.2, 2.9, .43, .4, .46], [4.0, 2.25, .58, .46, .66]
    ];
    const wallColors = [0xf0e4cc, 0xe4ded5, 0xd4dfe4, 0xe5cfb5];
    const roofs = [0xa85c3f, 0x546979, 0x7d5143, 0x52665b];
    const windowTransforms = [];
    sites.forEach(([x, z, width, depth, height], index) => {
      const y = Math.max(...[-1, 1].flatMap(dx => [-1, 1].map(dz => heightAt(x + dx * width / 2, z + dz * depth / 2))));
      const foundation = new T.Mesh(new T.BoxGeometry(width + .08, .11, depth + .08), new T.MeshStandardMaterial({color:0xb6b2a8,roughness:.95}));
      foundation.position.set(x, y + .02, z); foundation.receiveShadow = true; world.add(foundation);
      const wall = new T.Mesh(new T.BoxGeometry(width, height, depth), new T.MeshStandardMaterial({color:wallColors[index % wallColors.length],roughness:.85}));
      wall.position.set(x, y + height / 2 + .065, z); wall.castShadow = true; wall.receiveShadow = true; world.add(wall);
      const a = width / 2 + .04, b = depth / 2 + .045, ridge = .13;
      const roofShape = new T.Shape(); roofShape.moveTo(-a, 0); roofShape.lineTo(0, ridge); roofShape.lineTo(a, 0); roofShape.closePath();
      const roofGeometry = new T.ExtrudeGeometry(roofShape, { depth: b * 2, bevelEnabled: false, steps: 1 });
      const roof = new T.Mesh(roofGeometry, new T.MeshStandardMaterial({color:roofs[index % roofs.length],roughness:.75}));
      roof.position.set(x, y + height + .065, z - b); roof.castShadow = true; world.add(roof);
      for (let floor = 0; floor < (height > .4 ? 2 : 1); floor++) {
        for (let column = 0; column < 3; column++) {
          const wy = y + .18 + floor * .2;
          for (const face of [-1, 1]) {
            matrixObject.position.set(x + (column - 1) * width * .25, wy, z + face * (depth / 2 + .003));
            matrixObject.rotation.set(0, 0, 0); matrixObject.scale.set(1, 1, 1); matrixObject.updateMatrix();
            windowTransforms.push(matrixObject.matrix.clone());
          }
        }
      }
    });
    const windows = new T.InstancedMesh(new T.BoxGeometry(.062, .075, .008), new T.MeshStandardMaterial({color:0x547b91,metalness:.3,roughness:.3}), windowTransforms.length);
    windowTransforms.forEach((matrix,index)=>windows.setMatrixAt(index,matrix)); world.add(windows);

    // A timber mountain refuge beside the hiking route, on a stone platform.
    const hutX=-.65,hutZ=.65;
    const hutY=Math.max(...[-.25,.25].flatMap(dx=>[-.2,.2].map(dz=>heightAt(hutX+dx,hutZ+dz))));
    const hut=new T.Group();hut.position.set(hutX,hutY,hutZ);world.add(hut);
    function hutBox(w,h,d,x,y,z,color){
      const mesh=new T.Mesh(new T.BoxGeometry(w,h,d),new T.MeshStandardMaterial({color,roughness:.9}));
      mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;hut.add(mesh);return mesh;
    }
    hutBox(.6,.3,.49,0,-.09,0,0x92918a);
    hutBox(.5,.33,.4,0,.18,0,0x956640);
    for(let n=0;n<5;n++)hutBox(.51,.013,.412,0,.045+n*.061,0,0x68452e);
    const hutRoof=new T.Shape();hutRoof.moveTo(-.32,0);hutRoof.lineTo(0,.22);hutRoof.lineTo(.32,0);hutRoof.closePath();
    const roofMesh=new T.Mesh(new T.ExtrudeGeometry(hutRoof,{depth:.52,bevelEnabled:false}),new T.MeshStandardMaterial({color:0x5a3830,roughness:.85}));
    roofMesh.position.set(0,.35,-.26);roofMesh.castShadow=true;hut.add(roofMesh);
    hutBox(.095,.21,.018,-.11,.125,.21,0x483627);
    const hutWindow=hutBox(.1,.095,.02,.115,.23,.21,0x8caeb6);
    hutWindow.material=windows.material;
    hutBox(.055,.19,.065,.18,.49,-.09,0x6b6862);
    const treePositions = [];
    const maxTrees = mobile ? 170 : 290;
    for (let attempt = 0; attempt < 6500 && treePositions.length < maxTrees; attempt++) {
      const x = (random() - .5) * 9.5, z = (random() - .5) * 9.5, height = heightAt(x, z);
      if (Math.hypot(x-hutX,z-hutZ)<.6) continue;
      if (height > 1.95 || height < .045 || (z > 3.0 && random() > .16)) continue;
      if (Math.hypot(heightAt(x + .07, z) - height, heightAt(x, z + .07) - height) > .12) continue;
      if (roadSamples.some(([rx, rz]) => Math.hypot(x - rx, z - rz) < .2)) continue;
      if (sites.some(([bx, bz]) => Math.hypot(x - bx, z - bz) < .48)) continue;
      if ([[-3.4, 2.2], [1.35, -1.8], [3.15, 2.35]].some(([sx, sz]) => Math.hypot(x - sx, z - sz) < .48)) continue;
      if (treePositions.some(t=>Math.hypot(x-t.x,z-t.z)<.13)) continue;
      treePositions.push({x,z,y:height+.02,size:.19+random()*.2,variation:random()});
    }
    // Mixed mature garden trees at side/rear corners; keep road-facing fronts open.
    const gardens=[];
    sites.forEach(([bx,bz,w,d],i)=>{
      if(i%2!==0)return;
      for(const side of [-1,1]){
        const x=bx+side*(w/2+.19),z=bz+d/2+.13;
        if(Math.abs(x)>4.75||z>4.78)continue;
        if(roadSamples.some(([rx,rz])=>Math.hypot(x-rx,z-rz)<.4))continue;
        if(sites.some(([hx,hz,hw,hd])=>Math.abs(x-hx)<hw/2+.12&&Math.abs(z-hz)<hd/2+.12))continue;
        gardens.push({x,z});
        if(!treePositions.some(t=>Math.hypot(x-t.x,z-t.z)<.2)){
          const kind=(gardens.length-1)%3;
          treePositions.push({x,z,y:heightAt(x,z)+.02,size:.36+random()*.2,
            variation:kind===0?.2+random()*.25:.72+random()*.25,slender:kind===2});
        }
      }
    });
    const count = treePositions.length;
    // Shared geometry keeps the richer forest to four instanced draw calls.
    const bark = new T.MeshStandardMaterial({color:0x796047,roughness:1});
    const leaves = new T.MeshStandardMaterial({color:0xffffff,roughness:.93});
    const trunks = new T.InstancedMesh(new T.CylinderGeometry(.65,1,1,7),bark,count*9);
    const pine = new T.InstancedMesh(new T.IcosahedronGeometry(1,0),leaves,count*32);
    const canopy = new T.InstancedMesh(new T.IcosahedronGeometry(1,1),leaves,count*12);
    const shrubs = new T.InstancedMesh(new T.IcosahedronGeometry(1,1),leaves,count*3);
    const counts=new Map([[trunks,0],[pine,0],[canopy,0],[shrubs,0]]);
    function instance(mesh,position,scale,rotation,color){
      matrixObject.position.set(...position);matrixObject.scale.set(...scale);
      matrixObject.rotation.set(...rotation);matrixObject.updateMatrix();
      const index=counts.get(mesh);mesh.setMatrixAt(index,matrixObject.matrix);
      if(color)mesh.setColorAt(index,color);counts.set(mesh,index+1);
    }
    const green=(h,l)=>new T.Color().setHSL(h,.38+random()*.18,l,T.SRGBColorSpace);
    function branch(x,y,z,dx,dy,dz,radius){
      const direction=new T.Vector3(dx,dy,dz),length=direction.length();
      matrixObject.position.set(x+dx/2,y+dy/2,z+dz/2);
      matrixObject.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),direction.normalize());
      matrixObject.scale.set(radius,length,radius);matrixObject.updateMatrix();
      const index=counts.get(trunks);trunks.setMatrixAt(index,matrixObject.matrix);counts.set(trunks,index+1);
    }
    treePositions.forEach(({x,y,z,size,variation,slender=false})=>{
      // Foreground trees carry extra branches; distant/mobile trees use fewer clusters.
      const detailed=!mobile&&z>-.6,angle=variation*Math.PI*2;
      branch(x,y,z,size*.045,size*.85,0,size*.048);
      if(variation<.62){
        const tiers=detailed?5:3;
        for(let tier=0;tier<tiers;tier++){
          const f=tier/(tiers-1),spread=size*(.35-f*.24),cy=y+size*(.38+f*.64);
          const lobes=detailed?5:3;
          for(let n=0;n<lobes;n++){
            const a=angle+n*Math.PI*2/lobes+tier*1.7;
            instance(pine,[x+Math.cos(a)*spread*.55,cy+random()*size*.04,z+Math.sin(a)*spread*.55],
              [spread*.8,size*(.24-f*.09),spread*.62],[.1,a,.12],green(.31+variation*.05,.22+f*.09+random()*.035));
          }
          if(detailed&&tier<3)branch(x,cy-size*.12,z,Math.cos(angle+tier*2)*spread, size*.06,Math.sin(angle+tier*2)*spread,size*.015);
        }
        instance(pine,[x,y+size*1.09,z],[size*.09,size*.19,size*.09],[0,angle,0],green(.32,.33));
      }else{
        const lobes=detailed?9:5;
        for(let n=0;n<lobes;n++){
          const a=angle+n*2.39996,spread=size*(n===0?0:.18+random()*.12)*(slender?.5:1);
          const dx=Math.cos(a)*spread,dz=Math.sin(a)*spread,cy=size*(.67+random()*.33);
          if(n<4)branch(x,y+size*.35,z,dx,cy-size*.35,dz,size*.018);
          instance(canopy,[x+dx,y+cy,z+dz],[size*(.19+random()*.09)*(slender?.55:1),size*(.23+random()*.1)*(slender?1.45:1),size*(.19+random()*.09)*(slender?.55:1)],
            [random()*.5,a,random()*.4],green(.24+variation*.055,.28+random()*.13));
        }
      }
      if(variation>.8){
        for(let n=0;n<3;n++)instance(shrubs,[x+(n-1)*size*.13,y+size*.14,z+size*.18],
          [size*.18,size*.17,size*.16],[0,n*2,0],green(.25,.29+random()*.09));
      }
    });
    for(const mesh of [trunks,pine,canopy,shrubs]){
      mesh.count=counts.get(mesh);mesh.name='forest-'+(['trunks','pine','canopy','shrubs'][[trunks,pine,canopy,shrubs].indexOf(mesh)]);
      mesh.castShadow=true;mesh.receiveShadow=true;world.add(mesh);
    }
    // Three crossed, tapered blades per clump; one draw call for the meadow.
    const bladeVertices=[];
    for(let i=0;i<3;i++){
      const a=i*Math.PI/3,dx=Math.cos(a)*.12,dz=Math.sin(a)*.12;
      bladeVertices.push(-dx,0,-dz,dx,0,dz,.16*Math.cos(a+.4),1,.16*Math.sin(a+.4));
    }
    const bladeGeometry=new T.BufferGeometry();bladeGeometry.setAttribute('position',new T.Float32BufferAttribute(bladeVertices,3));bladeGeometry.computeVertexNormals();
    const meadow=new T.InstancedMesh(bladeGeometry,new T.MeshStandardMaterial({color:0xffffff,side:T.DoubleSide,roughness:1}),mobile?900:2400);
    meadow.name='meadow-grass';let grassCount=0;
    for(let attempt=0;attempt<16000&&grassCount<meadow.instanceMatrix.count;attempt++){
      const garden=attempt<gardens.length*35?gardens[Math.floor(attempt/35)]:null;
      const x=garden?garden.x+(random()-.5)*.3:(random()-.5)*9.3,z=garden?garden.z+(random()-.5)*.22:(random()-.5)*9.3,h=heightAt(x,z);
      if((!garden&&h<.015)||h>1.6||Math.hypot(heightAt(x+.04,z)-h,heightAt(x,z+.04)-h)>.05)continue;
      if(roadSamples.some(([rx,rz])=>Math.hypot(x-rx,z-rz)<.34))continue;
      if(sites.some(([bx,bz,w,d])=>Math.abs(x-bx)<w/2+.1&&Math.abs(z-bz)<d/2+.1))continue;
      if(Math.hypot(x-hutX,z-hutZ)<.5)continue;
      const size=.022+random()*.035;
      matrixObject.position.set(x,h+.019,z);matrixObject.rotation.set(0,random()*Math.PI*2,0);matrixObject.scale.set(size,size,size);matrixObject.updateMatrix();
      meadow.setMatrixAt(grassCount,matrixObject.matrix);meadow.setColorAt(grassCount,new T.Color().setHSL(.23+random()*.08,.35+random()*.2,.25+random()*.13,T.SRGBColorSpace));grassCount++;
    }
    meadow.count=grassCount;meadow.receiveShadow=true;world.add(meadow);
    const rocks = new T.InstancedMesh(new T.IcosahedronGeometry(1, 0),new T.MeshStandardMaterial({color:0x999c8f,roughness:1}),45);
    let rockCount=0;
    for(let n=0;n<400 && rockCount<45;n++){
      const x=(random()-.5)*7,z=(random()-.5)*7,y=heightAt(x,z);
      if(y<1.15||y>2.8)continue;
      const size=.045+random()*.07;matrixObject.position.set(x,y+.02,z);matrixObject.rotation.set(random()*2,random()*4,random()*2);matrixObject.scale.set(size,size*.7,size*.85);matrixObject.updateMatrix();rocks.setMatrixAt(rockCount++,matrixObject.matrix);
    }
    rocks.count=rockCount;rocks.castShadow=true;world.add(rocks);
    return { mainRoad, windows, obstacles: [...[[-3.4,2.2],[1.35,-1.8],[3.15,2.35]].map(([x,z])=>({x,z,w:.38,d:.38})), ...sites.map(([x,z,w,d])=>({x,z,w:w+.08,d:d+.08})), {x:hutX,z:hutZ,w:.6,d:.49}] };
  };
})();
