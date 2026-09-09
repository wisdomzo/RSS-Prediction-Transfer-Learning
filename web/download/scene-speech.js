/* Shared text textures and three reusable sprites for occasional greetings. */
(function(){
 'use strict';
 window.ASSETSpeech=function(T,world){
  const phrases=['Hi!','Hello!','Hey there!','How are you?','Nice day!','See you!','Have fun!','Looking good!'];
  const textures=phrases.map(text=>{
   const canvas=document.createElement('canvas');canvas.width=512;canvas.height=160;
   const ctx=canvas.getContext('2d');
   ctx.font='600 43px sans-serif';
   const width=Math.ceil(ctx.measureText(text).width)+64,center=width/2;canvas.width=width;
   ctx.fillStyle='#ffffff';ctx.strokeStyle='#435b75';ctx.lineWidth=4;
   ctx.beginPath();ctx.moveTo(28,8);ctx.lineTo(width-28,8);ctx.quadraticCurveTo(width-8,8,width-8,28);
   ctx.lineTo(width-8,112);ctx.quadraticCurveTo(width-8,132,width-28,132);ctx.lineTo(center+19,132);
   ctx.lineTo(center,154);ctx.lineTo(center-19,132);ctx.lineTo(28,132);ctx.quadraticCurveTo(8,132,8,112);
   ctx.lineTo(8,28);ctx.quadraticCurveTo(8,8,28,8);ctx.closePath();ctx.fill();ctx.stroke();
   ctx.font='600 43px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#23364d';ctx.fillText(text,center,72);
   const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;return texture;
  });
  const people=[];world.traverse(o=>{if(o.userData.speechHeight)people.push({person:o,wait:12+Math.random()*33});});
  const slots=Array.from({length:3},()=>{
   const sprite=new T.Sprite(new T.SpriteMaterial({map:textures[0],transparent:true,depthWrite:false,toneMapped:false}));
   sprite.name='speech-bubble';sprite.scale.set(.58,.181,1);sprite.visible=false;world.add(sprite);
   return {sprite,actor:null,remaining:0};
  });
  function visible(person){for(let p=person;p;p=p.parent)if(!p.visible)return false;return true;}
  let last=null,nextSpeech=0;
  return function update(elapsed){
   const dt=last===null?0:Math.max(0,Math.min(.05,elapsed-last));last=elapsed;
   nextSpeech=Math.max(0,nextSpeech-dt);
   for(const slot of slots){
    if(!slot.actor)continue;
    slot.remaining-=dt;
    if(slot.remaining<=0||!visible(slot.actor.person)){
     slot.actor.wait=45+Math.random()*45;slot.actor=null;slot.sprite.visible=false;continue;
    }
    const person=slot.actor.person;
    person.getWorldPosition(slot.sprite.position);world.worldToLocal(slot.sprite.position);
    slot.sprite.position.y+=person.userData.speechHeight+.12;
   }
   for(const actor of people){
    if(!visible(actor.person)||slots.some(s=>s.actor===actor))continue;
    actor.wait-=dt;
    if(actor.wait>0||nextSpeech>0)continue;
    const slot=slots.find(s=>!s.actor);if(!slot)continue;
    slot.actor=actor;slot.remaining=2.8+Math.random();
    slot.sprite.material.map=textures[Math.floor(Math.random()*textures.length)];
    slot.sprite.scale.set(.181*slot.sprite.material.map.image.width/160,.181,1);
    nextSpeech=8+Math.random()*8;
    actor.person.getWorldPosition(slot.sprite.position);world.worldToLocal(slot.sprite.position);
    slot.sprite.position.y+=actor.person.userData.speechHeight+.12;slot.sprite.visible=true;
   }
  };
 };
})();
