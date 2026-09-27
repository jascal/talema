const conversation=document.querySelector('#conversation'), form=document.querySelector('#composer'), input=document.querySelector('#message'), status=document.querySelector('#status'), language=document.querySelector('#captionLanguage'), player=document.querySelector('#localAudio');
let history=[], bubbles=[], generation=0, controller, audioUrl;
const suggestions=document.querySelector('#suggestions'), suggestionButtons=document.querySelector('#suggestionButtons');
let currentSuggestions=[];
function showSuggestions(items=[]) {
  currentSuggestions=items;
  suggestionButtons.replaceChildren();
  for(const item of items) {
    const button=document.createElement('button');button.type='button';button.className='suggestion';
    button.dataset.suggestion=item.talema;
    const talema=document.createElement('span');talema.className='suggestion-talema';talema.textContent=item.talema;
    const caption=document.createElement('span');caption.className='suggestion-caption';caption.textContent=item[language.value]||'';
    button.append(talema,caption);suggestionButtons.append(button);
  }
  suggestions.hidden=suggestionButtons.childElementCount===0;
}
function addBubble(kind,data) {
  const bubble=document.createElement('article');bubble.className=`bubble ${kind}`;
  for(const [tag,key] of [['div','talema'],['div','caption'],['small','source']]) {
    const el=document.createElement(tag);el.className=key;
    el.textContent=key==='caption'?(data[language.value]||''):(data[key]||'');bubble.append(el);
  }
  conversation.append(bubble);bubbles.push({bubble,data});bubble.scrollIntoView({behavior:'smooth',block:'nearest'});
}
async function post(path,body,signal) {
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});
  const data=await response.json();if(!response.ok)throw Error(data.error||`HTTP ${response.status}`);return data;
}
function audioBlob(encoded) { return new Blob([Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))],{type:'audio/wav'}); }
async function testVoice() {
  stop(); const turn=generation; controller=new AbortController();
  const text='veloma .';
  document.querySelector('#liveTalema').textContent=text;
  document.querySelector('#liveCaption').textContent='Welcome.';
  character.state('thinking'); status.textContent='Generating local Kokoro voice…';
  try {
    const speech=await post('/api/utterance',{talema:text},controller.signal);
    if(turn!==generation)return;
    if(audioUrl)URL.revokeObjectURL(audioUrl);
    audioUrl=URL.createObjectURL(audioBlob(speech.audio)); player.src=audioUrl;
    character.load(speech.cues,'warm');
    try { await player.play(); document.querySelector('#playReply').hidden=true; status.textContent=`Local voice works: ${speech.provider} / ${speech.voice}.`; }
    catch { document.querySelector('#playReply').hidden=false; status.textContent=`Audio is ready (${speech.provider} / ${speech.voice}); click Play reply.`; }
  } catch(error) { if(turn===generation){character.state('idle');status.textContent=`Voice test failed: ${error.message}. Start with uv run --extra tts python avatar/server.py.`;} }
}
function stop() { generation++;controller?.abort();player.pause();character.state('idle'); }
async function send(text,start=false) {
  stop();const turn=generation;controller=new AbortController();const signal=controller.signal;
  showSuggestions();
  if(start){history=[];conversation.replaceChildren();bubbles=[];}
  else addBubble('user',{talema:text});
  character.state('thinking');status.textContent='Luma is preparing a reply…';
  try {
    const data=await post('/api/respond',{talema:text,history:history.slice(-24),start},signal);
    if(turn!==generation)return;
    history.push({role:'user',content:start?'Begin a beginner lesson.':text},{role:'assistant',content:data.talema});
    addBubble('avatar',data);status.textContent='Preparing local speech…';
    showSuggestions(data.suggestions||[]);
    const speech=await post('/api/utterance',{talema:data.talema},signal);
    if(turn!==generation)return;
    if(audioUrl)URL.revokeObjectURL(audioUrl);
    audioUrl=URL.createObjectURL(audioBlob(speech.audio));
    player.src=audioUrl;character.load(speech.cues,data.emotion);
    document.querySelector('#liveTalema').textContent=data.talema;
    document.querySelector('#liveCaption').textContent=data[language.value];
    player.dataset.caption=JSON.stringify(data);
    try {await player.play();status.textContent=`${data.source} · ${speech.provider} / ${speech.voice}`;}
    catch {character.state('idle');document.querySelector('#playReply').hidden=false;status.textContent='Reply ready. Browser blocked automatic playback; press Play reply.';}
    if(!player.paused)document.querySelector('#playReply').hidden=true;
  } catch(error) {if(turn===generation){character.state('idle');status.textContent=error.message;}}
}
player.addEventListener('play',()=>character.state('speaking'));
player.addEventListener('pause',()=>character.state('idle'));
player.addEventListener('ended',()=>character.state('listening'));
form.addEventListener('submit',e=>{e.preventDefault();const text=input.value.trim();if(text){input.value='';send(text);}});
document.querySelector('#start').onclick=()=>send('',true);
document.querySelector('#testVoice').onclick=testVoice;
document.querySelector('#stop').onclick=()=>{stop();status.textContent='Stopped. Your turn.';};
document.querySelector('#playReply').onclick=async()=>{try{await player.play();document.querySelector('#playReply').hidden=true;}catch(error){status.textContent=`Could not play reply: ${error.message}`;}};
suggestionButtons.addEventListener('click',event=>{
  const button=event.target.closest('[data-suggestion]');
  if(button)send(button.dataset.suggestion);
});
language.onchange=()=>{bubbles.forEach(({bubble,data})=>bubble.querySelector('.caption').textContent=data[language.value]||'');if(player.dataset.caption)document.querySelector('#liveCaption').textContent=JSON.parse(player.dataset.caption)[language.value];showSuggestions(currentSuggestions);};
const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
let recognition;
document.querySelector('#mic').onclick=()=>{
  if(!Recognition){status.textContent='Speech recognition is unavailable; type your message.';return;}
  if(recognition){recognition.stop();return;}
  stop();recognition=new Recognition();recognition.lang='it-IT';
  character.state('listening');status.textContent='Listening. Review the transcript before sending; recognition is not trained for Talema.';
  recognition.onresult=e=>{input.value=e.results[0][0].transcript;input.focus();};
  recognition.onerror=()=>{status.textContent='Could not transcribe. Please type your message.';};
  recognition.onend=()=>{recognition=null;character.state('idle');};recognition.start();
};
fetch('/api/health').then(r=>r.json()).then(data=>{
  status.textContent=data.dialogue.configured?`Tutor configured: ${data.dialogue.model}. Start a lesson when ready.`:'Start a lesson to hear the local greeting. Set OPENAI_API_KEY and TALEMA_MODEL on the server to enable conversation.';
}).catch(()=>status.textContent='Cannot reach the local avatar server.');
