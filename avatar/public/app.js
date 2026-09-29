// Talema avatar client. The avatar is a local canvas character; the tutor is the
// OpenAI Responses API; the voice is local Kokoro. State lives in the browser tab
// only. Refreshing the page clears history.
(() => {
  'use strict';

  const conversationEl = document.querySelector('#conversation');
  const formEl = document.querySelector('#composer');
  const inputEl = document.querySelector('#message');
  const statusEl = document.querySelector('#status');
  const languageEl = document.querySelector('#captionLanguage');
  const playerEl = document.querySelector('#localAudio');
  const suggestionsEl = document.querySelector('#suggestions');
  const suggestionButtonsEl = document.querySelector('#suggestionButtons');
  const liveTalemaEl = document.querySelector('#liveTalema');
  const liveCaptionEl = document.querySelector('#liveCaption');
  const startBtn = document.querySelector('#start');
  const testVoiceBtn = document.querySelector('#testVoice');
  const stopBtn = document.querySelector('#stop');
  const playReplyBtn = document.querySelector('#playReply');
  const micBtn = document.querySelector('#mic');
  const starterChipsEl = document.querySelector('#starterChips');
  const playbackEl = document.querySelector('#playback');
  const playbackFillEl = document.querySelector('#playbackFill');
  const playbackTimeEl = document.querySelector('#playbackTime');

  const CAPTION_FALLBACK = { en: 'Welcome.', es: 'Bienvenido.', de: 'Willkommen.' };
  const TEST_PHRASE = 'veloma .';

  // Per-turn state. `generation` is bumped on every Stop or new request so async
  // responses from older turns are discarded.
  let history = [];
  let bubbles = [];
  let currentSuggestions = [];
  let generation = 0;
  let controller = null;
  let audioUrl = null;
  // Word highlight state for the live subtitles; rebuilt every reply.
  let wordSpans = [];
  let wordCues = [];
  let activeWordIndex = -1;
  let recognition = null;

  function selectedLanguage() { return languageEl.value; }

  function captionText(data, lang) { return (data && data[lang]) || ''; }

  function currentCaption(data) { return captionText(data, selectedLanguage()); }

  function setStatus(text) { statusEl.textContent = text; }

  function showSuggestions(items = []) {
    currentSuggestions = items;
    suggestionButtonsEl.replaceChildren();
    for (const item of items) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'suggestion';
      button.dataset.suggestion = item.talema;
      const talema = document.createElement('span');
      talema.className = 'suggestion-talema';
      talema.textContent = item.talema;
      const caption = document.createElement('span');
      caption.className = 'suggestion-caption';
      caption.textContent = captionText(item, selectedLanguage());
      button.append(talema, caption);
      suggestionButtonsEl.append(button);
    }
    suggestionsEl.hidden = suggestionButtonsEl.childElementCount === 0;
  }

  function renderBubble(kind, data) {
    const bubble = document.createElement('article');
    bubble.className = `bubble ${kind}`;
    const talema = document.createElement('div');
    talema.className = 'talema';
    talema.textContent = data.talema || '';
    const caption = document.createElement('div');
    caption.className = 'caption';
    caption.textContent = currentCaption(data);
    const source = document.createElement('small');
    source.className = 'source';
    source.textContent = data.source || '';
    bubble.append(talema, caption, source);
    if (kind === 'avatar' && data.talema) {
      const replay = document.createElement('button');
      replay.type = 'button';
      replay.className = 'replay';
      replay.textContent = '↻ Replay';
      replay.setAttribute('aria-label', 'Replay this reply');
      replay.dataset.payload = JSON.stringify(data);
      bubble.append(replay);
    }
    conversationEl.append(bubble);
    bubbles.push({ bubble, data });
    bubble.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    return bubble;
  }

  // Per-word live subtitle rendering. Each spoken word gets its own span, while
  // punctuation stays as plain text, so the subtitle reads exactly like the stored
  // sentence. The cues are a parameter, not something the caller sets afterwards:
  // rendering and cue-assignment have to happen together or the highlight silently
  // never runs, so this owns both.
  const WORD_CHUNK = /[A-Za-zÀ-ÿ0-9]/;
  function renderLiveTalema(text, cues) {
    liveTalemaEl.replaceChildren();
    wordSpans = [];
    wordCues = Array.isArray(cues) ? cues : [];
    activeWordIndex = -1;
    for (const chunk of String(text || '').split(' ')) {
      if (WORD_CHUNK.test(chunk)) {
        const span = document.createElement('span');
        span.className = 'word';
        span.textContent = chunk;
        liveTalemaEl.append(span);
        wordSpans.push(span);
      } else if (chunk) {
        liveTalemaEl.append(document.createTextNode(chunk));
      }
      liveTalemaEl.append(document.createTextNode(' '));
    }
  }

  function setActiveWord(index) {
    if (index === activeWordIndex) return;
    if (activeWordIndex >= 0 && wordSpans[activeWordIndex]) {
      wordSpans[activeWordIndex].classList.remove('active');
    }
    if (index >= 0 && wordSpans[index]) {
      wordSpans[index].classList.add('active');
    }
    activeWordIndex = index;
  }

  function findActiveWordIndex(time) {
    if (!wordCues.length) return -1;
    for (let i = 0; i < wordCues.length; i++) {
      if (time >= wordCues[i].start && time < wordCues[i].end) return i;
    }
    return time >= wordCues[wordCues.length - 1].end ? wordCues.length - 1 : -1;
  }

  // Drive the active-word highlighter from the audio clock. Cheap linear scan per
  // tick; with at most a few dozen words per turn this is negligible. The playback
  // readout rides the same tick rather than starting a second animation loop.
  function clock(seconds) {
    const total = Math.max(0, Math.floor(seconds || 0));
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
  }

  function tickWordHighlight() {
    if (!playerEl.paused && !playerEl.ended && wordCues.length) {
      setActiveWord(findActiveWordIndex(playerEl.currentTime));
    }
    const duration = playerEl.duration;
    if (Number.isFinite(duration) && duration > 0) {
      playbackEl.hidden = false;
      playbackFillEl.style.width = `${Math.min(100, (playerEl.currentTime / duration) * 100)}%`;
      playbackTimeEl.textContent = `${clock(playerEl.currentTime)} / ${clock(duration)}`;
    } else {
      playbackEl.hidden = true;
    }
    requestAnimationFrame(tickWordHighlight);
  }
  requestAnimationFrame(tickWordHighlight);

  async function post(path, body, signal) {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  function audioBlob(encoded) {
    return new Blob([Uint8Array.from(atob(encoded), c => c.charCodeAt(0))], { type: 'audio/wav' });
  }

  function describeUsage(usage, source) {
    if (!usage || !usage.input_tokens) return source || '';
    const cached = usage.cached_tokens || 0;
    const ratio = cached / usage.input_tokens;
    const cacheNote = cached
      ? ` · ${Math.round(ratio * 100)}% cached (${cached.toLocaleString()}/${usage.input_tokens.toLocaleString()} tokens)`
      : '';
    return `${source || ''}${cacheNote}`;
  }

  async function playUtterance(speech, data, turn) {
    if (turn !== generation) return;
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = URL.createObjectURL(audioBlob(speech.audio));
    playerEl.src = audioUrl;
    window.character.load(speech.cues, data.emotion);
    renderLiveTalema(data.talema, speech.word_cues);
    liveCaptionEl.textContent = currentCaption(data);
    playerEl.dataset.caption = JSON.stringify(data);
    try {
      await playerEl.play();
      playReplyBtn.hidden = true;
      setStatus(describeUsage(data.usage, `${data.source} · ${speech.provider} / ${speech.voice}`));
    } catch {
      window.character.state('idle');
      playReplyBtn.hidden = false;
      setStatus('Reply ready. Browser blocked automatic playback; press Play reply.');
    }
    if (!playerEl.paused) playReplyBtn.hidden = true;
  }

  async function testVoice() {
    stop();
    const turn = generation;
    controller = new AbortController();
    liveTalemaEl.textContent = TEST_PHRASE;
    liveCaptionEl.textContent = CAPTION_FALLBACK[selectedLanguage()] || CAPTION_FALLBACK.en;
    window.character.state('thinking');
    setStatus('Generating local Kokoro voice…');
    try {
      const speech = await post('/api/utterance', { talema: TEST_PHRASE }, controller.signal);
      if (turn !== generation) return;
      await playUtterance(speech, { talema: TEST_PHRASE, source: 'local test', en: CAPTION_FALLBACK.en,
                                     es: CAPTION_FALLBACK.es, de: CAPTION_FALLBACK.de }, turn);
    } catch (error) {
      if (turn === generation) {
        window.character.state('idle');
        setStatus(`Voice test failed: ${error.message}. Start with uv run --extra tts python avatar/server.py.`);
      }
    }
  }

  function stop() {
    generation += 1;
    if (controller) controller.abort();
    playerEl.pause();
    setActiveWord(-1);
    window.character.state('idle');
  }

  async function send(text, start = false) {
    stop();
    const turn = generation;
    controller = new AbortController();
    const signal = controller.signal;
    showSuggestions();
    if (start) {
      history = [];
      conversationEl.replaceChildren();
      bubbles = [];
    } else {
      renderBubble('user', { talema: text });
    }
    window.character.state('thinking');
    setStatus(start ? 'Starting a fresh lesson…' : 'Luma is preparing a reply…');
    try {
      const data = await post(
        '/api/respond',
        { talema: text, history: history.slice(-24), start },
        signal,
      );
      if (turn !== generation) return;
      history.push(
        { role: 'user', content: start ? 'Begin a beginner lesson.' : text },
        { role: 'assistant', content: data.talema },
      );
      renderBubble('avatar', data);
      showSuggestions(data.suggestions || []);
      setStatus('Preparing local speech…');
      const speech = await post('/api/utterance', { talema: data.talema }, signal);
      await playUtterance(speech, data, turn);
    } catch (error) {
      if (turn === generation) {
        window.character.state('idle');
        setStatus(error.message);
      }
    }
  }

  // Replay an existing avatar bubble by replaying its saved utterance payload.
  async function replayBubble(button) {
    const data = JSON.parse(button.dataset.payload);
    stop();
    const turn = generation;
    controller = new AbortController();
    window.character.state('thinking');
    setStatus('Replaying…');
    try {
      const speech = await post('/api/utterance', { talema: data.talema }, controller.signal);
      await playUtterance(speech, data, turn);
    } catch (error) {
      if (turn === generation) {
        window.character.state('idle');
        setStatus(`Could not replay: ${error.message}`);
      }
    }
  }

  // Event wiring.
  playerEl.addEventListener('play', () => { setActiveWord(-1); window.character.state('speaking'); });
  playerEl.addEventListener('pause', () => { window.character.state('idle'); });
  playerEl.addEventListener('ended', () => { setActiveWord(-1); window.character.state('listening'); });

  formEl.addEventListener('submit', event => {
    event.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = '';
    send(text);
  });

  startBtn.addEventListener('click', () => send('', true));
  testVoiceBtn.addEventListener('click', testVoice);
  stopBtn.addEventListener('click', () => { stop(); setStatus('Stopped. Your turn.'); });
  playReplyBtn.addEventListener('click', async () => {
    try { await playerEl.play(); playReplyBtn.hidden = true; }
    catch (error) { setStatus(`Could not play reply: ${error.message}`); }
  });

  suggestionButtonsEl.addEventListener('click', event => {
    const button = event.target.closest('[data-suggestion]');
    if (button) send(button.dataset.suggestion);
  });

  // The empty state carries the same affordance as the running conversation, so the
  // two share one shape and one handler rather than teaching the page two patterns.
  starterChipsEl.addEventListener('click', event => {
    const button = event.target.closest('[data-suggestion]');
    if (button) send(button.dataset.suggestion);
  });

  conversationEl.addEventListener('click', event => {
    const replay = event.target.closest('button.replay');
    if (replay) replayBubble(replay);
  });

  languageEl.addEventListener('change', () => {
    for (const { bubble, data } of bubbles) {
      bubble.querySelector('.caption').textContent = currentCaption(data);
    }
    if (playerEl.dataset.caption) {
      liveCaptionEl.textContent = currentCaption(JSON.parse(playerEl.dataset.caption));
    }
    showSuggestions(currentSuggestions);
  });

  // Escape stops whatever is in flight, from anywhere on the page. The listener sits
  // on the document alone: a keydown from the input bubbles up to it, so binding it in
  // both places would stop twice on every press.
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (recognition) recognition.stop();
    stop();
    setStatus('Stopped. Your turn.');
  });

  // Voice input uses browser recognition with an Italian locale; it is not trained
  // on Talema, so the learner should review the transcript before sending.
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  micBtn.addEventListener('click', () => {
    if (!Recognition) {
      setStatus('Speech recognition is unavailable; type your message.');
      return;
    }
    if (recognition) { recognition.stop(); return; }
    stop();
    recognition = new Recognition();
    recognition.lang = 'it-IT';
    window.character.state('listening');
    setStatus('Listening. Review the transcript before sending; recognition is not trained for Talema.');
    recognition.onresult = e => { inputEl.value = e.results[0][0].transcript; inputEl.focus(); };
    recognition.onerror = () => { setStatus('Could not transcribe. Please type your message.'); };
    recognition.onend = () => { recognition = null; window.character.state('idle'); };
    recognition.start();
  });

  fetch('/api/health').then(r => r.json()).then(data => {
    setStatus(data.dialogue.configured
      ? `Tutor configured: ${data.dialogue.model}. Start a lesson when ready.`
      : 'Start a lesson to hear the local greeting. Set OPENAI_API_KEY and TALEMA_MODEL on the server to enable conversation.');
  }).catch(() => setStatus('Cannot reach the local avatar server.'));
})();