// A local, real-time character. Mouth cues come from Kokoro's predicted durations.
(() => {
const canvas = document.querySelector('#character');
const ctx = canvas.getContext('2d');
const player = document.querySelector('#localAudio');
let cues = [], mood = 'warm', state = 'idle';
window.character = {
  load(next, emotion) { cues = next; mood = emotion || 'warm'; },
  state(next) { state = next; document.querySelector('#characterState').textContent = next; }
};
const shapes = {rest:[19,2],closed:[21,1],round:[10,15],wide:[26,8],open:[20,20],teeth:[22,5],small:[16,8]};
let mouth = [19,2];
function ellipse(x,y,rx,ry,color) { ctx.fillStyle=color; ctx.beginPath(); ctx.ellipse(x,y,rx,ry,0,0,Math.PI*2); ctx.fill(); }
function draw(ms) {
  const t=ms/1000, speaking=!player.paused && !player.ended;
  const cue = speaking ? cues.find(c=>player.currentTime>=c.start && player.currentTime<c.end) : null;
  const target=shapes[cue?.shape || 'rest'];
  mouth=mouth.map((v,i)=>v+(target[i]-v)*.65);
  ctx.clearRect(0,0,640,480);
  const glow=ctx.createRadialGradient(320,210,20,320,240,300);
  glow.addColorStop(0,'#34535a'); glow.addColorStop(1,'#111923'); ctx.fillStyle=glow;ctx.fillRect(0,0,640,480);
  ctx.save();ctx.translate(0,Math.sin(t*1.5)*2);
  // Pink football jersey, white Adidas shoulder stripes and chest mark.
  ellipse(320,481,155,137,'#d93d83'); ellipse(320,454,118,101,'#f064a2');
  ctx.strokeStyle='#fff1f7';ctx.lineWidth=5;ctx.lineCap='round';ctx.lineJoin='round';
  for(const side of [-1,1]) {
    for(let stripe=0;stripe<3;stripe++) {
      // Shift parallel tracks along the slope's normal, leaving pink gaps between them.
      const offset=55-stripe*5, y=364+stripe*8;
      ctx.beginPath();ctx.moveTo(320+side*offset,y);
      ctx.bezierCurveTo(320+side*(offset+25),y+13,
                        320+side*(offset+48),y+35,
                        320+side*(offset+70),y+48);ctx.stroke();
    }
  }
  // A small, clean three-stripe Adidas mark on the chest.
  ctx.fillStyle='#fff7fb';
  for(let i=0;i<3;i++) {
    ctx.beginPath();ctx.moveTo(306+i*9,420);ctx.lineTo(312+i*9,410-i*3);ctx.lineTo(317+i*9,410-i*3);ctx.lineTo(313+i*9,420);ctx.closePath();ctx.fill();
  }
  ctx.font='bold 10px Arial, sans-serif';ctx.textAlign='center';ctx.fillText('adidas',320,437);
  ctx.textAlign='start';
  ctx.fillStyle='#9b774d';ctx.fillRect(293,303,54,76);
  ellipse(320,354,29,20,'#9b774d');
  // Blonde curls frame the face and form a soft crown.
  ellipse(320,225,108,170,'#a87328');
  for(const [x,y,r] of [[241,163,21],[251,120,19],[270,91,20],[297,77,19],[326,73,21],[356,79,20],[385,96,19],[405,125,20],[411,163,18],[237,202,17],[403,202,17]]) {
    ellipse(x,y,r,r*.92,'#f0c457');
    ellipse(x-4,y-5,r*.42,r*.35,'#ffdf80');
  }
  // Long curled side locks fall over the shoulders, behind the ears and face.
  for(const side of [-1,1]) {
    ctx.fillStyle='#c68a30';ctx.beginPath();
    ctx.moveTo(320+side*78,137);
    ctx.bezierCurveTo(320+side*111,187,320+side*99,226,320+side*91,260);
    ctx.bezierCurveTo(320+side*82,299,320+side*103,332,320+side*87,366);
    ctx.bezierCurveTo(320+side*81,382,320+side*69,391,320+side*62,393);
    ctx.bezierCurveTo(320+side*71,367,320+side*59,350,320+side*66,324);
    ctx.bezierCurveTo(320+side*49,283,320+side*57,243,320+side*57,205);
    ctx.closePath();ctx.fill();
    ctx.strokeStyle='#f5ce69';ctx.lineWidth=4;ctx.lineCap='round';
    ctx.beginPath();ctx.moveTo(320+side*86,178);ctx.bezierCurveTo(320+side*76,225,320+side*78,262,320+side*85,288);ctx.stroke();
    ellipse(320+side*64,374,9,12,'#e5b64d');
  }
  ellipse(223,236,17,28,'#b9895e');ellipse(417,236,17,28,'#b9895e');
  // Tiny pink heart earrings with a soft gold stud at each lobe.
  for(const x of [222,418]) {
    ellipse(x,255,3.2,3.2,'#f5d474');
    ctx.save();ctx.translate(x,265);ctx.scale(.62,.62);
    ctx.fillStyle='#f071a6';ctx.strokeStyle='#ffe0eb';ctx.lineWidth=1.5;
    ctx.beginPath();ctx.moveTo(0,10);ctx.bezierCurveTo(-5,6,-13,1,-12,-5);ctx.bezierCurveTo(-11,-13,-2,-13,0,-7);ctx.bezierCurveTo(3,-13,12,-13,12,-5);ctx.bezierCurveTo(13,1,5,6,0,10);ctx.closePath();ctx.fill();ctx.stroke();
    ctx.restore();
  }
  // Gentle cheek width and a narrower, softly angled chin.
  ctx.fillStyle='#c39b6d';ctx.beginPath();ctx.moveTo(320,109);
  ctx.bezierCurveTo(377,109,410,158,412,213);
  ctx.bezierCurveTo(415,267,399,310,369,335);
  ctx.quadraticCurveTo(347,351,320,354);ctx.quadraticCurveTo(293,351,271,335);
  ctx.bezierCurveTo(241,310,225,267,228,213);
  ctx.bezierCurveTo(230,158,263,109,320,109);ctx.closePath();ctx.fill();
  ctx.fillStyle='#e9b84a';ctx.beginPath();ctx.moveTo(225,211);ctx.bezierCurveTo(209,41,433,47,421,216);ctx.bezierCurveTo(387,194,376,125,360,123);ctx.bezierCurveTo(323,180,263,157,225,211);ctx.fill();
  // Gaze and blinks; a thoughtful glance while preparing a turn.
  const blink=(t%4.7>4.55)? .12:1;
  const gaze=state==='thinking'?4:Math.sin(t*.35)*1.5;
  for(const x of [282,359]) {
    ellipse(x,229,20,10*blink,'#fff0df');ellipse(x+gaze,229,7,9*blink,'#425b50');ellipse(x+gaze,229,3,6*blink,'#18282a');
    ctx.strokeStyle='#473137';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(x-19,207);ctx.quadraticCurveTo(x, mood==='curious'?195:201,x+17,205);ctx.stroke();
  }
  ctx.strokeStyle='#9e7856';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(319,239);ctx.lineTo(313,262);ctx.quadraticCurveTo(320,268,327,261);ctx.stroke();
  // Soft rose lipstick stays visible at rest and follows each speaking shape.
  const open=Math.max(0,Math.min(1,(mouth[1]-8)/12));
  // At wide openings, use a tapered jaw shape instead of a symmetric oval.
  function mouthShape(rx,ry,color,spread=0) {
    ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(320-rx,293);
    ctx.bezierCurveTo(320-rx*.72,291-ry*.32,320-rx*.32,292-ry,320,292-ry);
    ctx.bezierCurveTo(320+rx*.32,292-ry,320+rx*.72,291-ry*.32,320+rx,293);
    ctx.bezierCurveTo(320+rx*.82,294+ry*.4,320+rx*.48,294+ry,320,294+ry+spread);
    ctx.bezierCurveTo(320-rx*.48,294+ry,320-rx*.82,294+ry*.4,320-rx,293);
    ctx.closePath();ctx.fill();
  }
  mouthShape(mouth[0]+3,Math.max(4,mouth[1]+3),'#b84f70',open*3);
  mouthShape(mouth[0],Math.max(1,mouth[1]-1),'#572638',open*2);
  if(mouth[1]>4) {
    mouthShape(mouth[0]-3,Math.max(1,mouth[1]-3),'#402832',open);
    ctx.fillStyle='#fff0df';ctx.beginPath();ctx.moveTo(306,289);ctx.quadraticCurveTo(320,287,334,289);ctx.lineTo(333,292);ctx.quadraticCurveTo(320,290,307,292);ctx.closePath();ctx.fill();
  }
  ctx.strokeStyle='#e58ba0';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(298,291);ctx.quadraticCurveTo(308,287,316,291);ctx.quadraticCurveTo(320,294,324,291);ctx.quadraticCurveTo(333,287,342,291);ctx.stroke();
  ctx.strokeStyle='#8c3852';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(299,295);ctx.quadraticCurveTo(320,304,341,295);ctx.stroke();
  ctx.strokeStyle='#8ee5c0';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(294,380);ctx.lineTo(320,403);ctx.lineTo(346,380);ctx.stroke();ellipse(320,403,5,7,'#8ee5c0');
  ctx.restore(); requestAnimationFrame(draw);
}
requestAnimationFrame(draw);
})();
