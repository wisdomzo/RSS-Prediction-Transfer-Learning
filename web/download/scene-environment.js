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
    const mainRoad = road([[-4.9, 3.65], [-2.6, 3.5], [-0.5, 3.85], [1.8, 3.7], [4.9, 3.25]], 0.19);
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

    const treePositions = [];
    const maxTrees = mobile ? 170 : 290;
    for (let attempt = 0; attempt < 6500 && treePositions.length < maxTrees; attempt++) {
      const x = (random() - .5) * 9.5, z = (random() - .5) * 9.5, height = heightAt(x, z);
      if (height > 1.95 || height < .045 || (z > 3.0 && random() > .16)) continue;
      if (Math.hypot(heightAt(x + .07, z) - height, heightAt(x, z + .07) - height) > .12) continue;
      if (roadSamples.some(([rx, rz]) => Math.hypot(x - rx, z - rz) < .2)) continue;
      if (sites.some(([bx, bz]) => Math.hypot(x - bx, z - bz) < .48)) continue;
      if ([[-3.4, 2.2], [1.35, -1.8], [3.15, 2.35]].some(([sx, sz]) => Math.hypot(x - sx, z - sz) < .48)) continue;
      if (treePositions.some(t=>Math.hypot(x-t.x,z-t.z)<.13)) continue;
      treePositions.push({x,z,y:height+.02,size:.19+random()*.2,variation:random()});
    }
    const count = treePositions.length;
    const trunks = new T.InstancedMesh(new T.CylinderGeometry(.012, .018, 1, 5), new T.MeshStandardMaterial({color:0x745b3d,roughness:1}), count);
    const pine = new T.InstancedMesh(new T.ConeGeometry(1, 1, 7), new T.MeshStandardMaterial({color:0xffffff,roughness:.92}), count * 2);
    const canopy = new T.InstancedMesh(new T.IcosahedronGeometry(1, 1), new T.MeshStandardMaterial({color:0xffffff,roughness:.95}), count);
    let pineCount=0, canopyCount=0;
    treePositions.forEach((tree,index)=>{
      const {x,y,z,size,variation}=tree;
      matrixObject.position.set(x,y+size*.4,z);matrixObject.rotation.set(0,variation*6.28,0);matrixObject.scale.set(1,size*.8,1);matrixObject.updateMatrix();trunks.setMatrixAt(index,matrixObject.matrix);
      if(variation<.68){
        for(let tier=0;tier<2;tier++){
          matrixObject.position.set(x,y+size*(.64+tier*.25),z);matrixObject.scale.set(size*(.37-tier*.08),size*.75,size*(.37-tier*.08));matrixObject.updateMatrix();pine.setMatrixAt(pineCount,matrixObject.matrix);
          pine.setColorAt(pineCount,new T.Color().setHSL(.30+variation*.05,.32+variation*.2,.22+variation*.08+tier*.025,T.SRGBColorSpace));pineCount++;
        }
      }else{
        matrixObject.position.set(x,y+size*.8,z);matrixObject.scale.set(size*.42,size*.5,size*.4);matrixObject.updateMatrix();canopy.setMatrixAt(canopyCount,matrixObject.matrix);
        canopy.setColorAt(canopyCount,new T.Color().setHSL(.24+variation*.05,.43,.29+variation*.09,T.SRGBColorSpace));canopyCount++;
      }
    });
    pine.count=pineCount;canopy.count=canopyCount;
    for(const mesh of [trunks,pine,canopy]){mesh.castShadow=true;mesh.receiveShadow=true;world.add(mesh);}
    const rocks = new T.InstancedMesh(new T.IcosahedronGeometry(1, 0),new T.MeshStandardMaterial({color:0x999c8f,roughness:1}),45);
    let rockCount=0;
    for(let n=0;n<400 && rockCount<45;n++){
      const x=(random()-.5)*7,z=(random()-.5)*7,y=heightAt(x,z);
      if(y<1.15||y>2.8)continue;
      const size=.045+random()*.07;matrixObject.position.set(x,y+.02,z);matrixObject.rotation.set(random()*2,random()*4,random()*2);matrixObject.scale.set(size,size*.7,size*.85);matrixObject.updateMatrix();rocks.setMatrixAt(rockCount++,matrixObject.matrix);
    }
    rocks.count=rockCount;rocks.castShadow=true;world.add(rocks);
  };
})();
