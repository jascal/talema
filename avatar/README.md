# Talema avatar

Luma is a local rendered 2D character with an LLM tutor and local Kokoro speech.
Spoken and written dialogue stays in Talema; English, Spanish and German captions
are separate. The character uses mouth shapes timed from Kokoro's predicted
phoneme durations, plus blinking, gaze and breathing. This is a real-time canvas
character, not photorealistic generated video or a video export pipeline.

## Run

From the repository root, copy `.env.example` to `.env`, create an API key at
<https://platform.openai.com/api-keys>, and paste it in place of the placeholder:

```sh
uv sync --extra tts
cp .env.example .env
# edit .env and replace OPENAI_API_KEY
uv run --extra tts python avatar/server.py
```

Open <http://127.0.0.1:8765>. Click **Test voice** first; it plays a local greeting
without calling the model. **Start a lesson** asks the model to open: greet, say one short sentence to learn, and invite an answer. If the
model is not configured or fails, it speaks the book's greeting `veloma` (“Welcome”) instead. Restart an already running
server and refresh the page after updating. Without model credentials, Start a lesson
speaks a short greeting from the book; follow-up conversation needs the credentials
above. If browser autoplay is blocked after generation, press **Play reply**. The
example uses GPT-5.4 Mini, which supports the Responses API and structured outputs
with a 400,000 token context. Credentials stay on the server. API usage is billed
separately from a ChatGPT subscription; conversation turns and all seven books are
sent to OpenAI on each turn (with `store: false`), and prompt caching makes repeat turns cheap (see below). If configuration is missing,
the local book greeting works, and follow-up model replies show a setup error.
If the API reports `insufficient_quota`, add API billing/credits or adjust the
project or organization spend limit; a ChatGPT subscription does not fund API calls.
If it reports a rate limit, wait and retry. OpenAI's [429 troubleshooting guide](https://help.openai.com/en/articles/5955604-troubleshooting-api-rate-limits-and-429-errors)
explains the codes.

Kokoro defaults to Italian `if_sara`, raw Talema phonemes, speed 0.92.
`TALEMA_KOKORO_VOICE`, `TALEMA_KOKORO_LANG` and `TALEMA_KOKORO_REPO_ID`
override the voice setup. The animated route requires Kokoro. First use may download
its model/voice. Keep the existing eSpeak installation required by Kokoro's pipeline.

## Interaction

- **Start a lesson** resets history and asks Luma to greet, demonstrate, and invite practice.
- After each model reply, Luma offers two or three context-aware Talema utterances as buttons, each with a translation in the selected caption language. Clicking one sends that phrase as the learner's next turn; without model configuration, the offline greeting has no generated suggestions.
- The opening asks which topic the learner wants. Later turns should stay with the learner's
  stated interest, answer their actual point, and ask a specific follow-up or offer a related
  example; they should not repeat broad topic-selection questions or greetings.
- The tutor is prompted to remember recent turns, acknowledge intent, recast mistakes,
  simplify after confusion, and offer one useful next step. These are prompted
  behaviors, not a claim of evaluated teaching competence.
- **Stop** cancels pending browser requests and pauses speech. You can interrupt with
  another message. A request already submitted to the model may still finish/bill.
- Audio controls pause/replay/seek; mouth movement follows the audio clock.
- Captions switch independently and are never synthesized. Subtitles currently
  show the whole utterance, not individual word highlighting.
- Microphone input uses browser recognition with an Italian locale, which is not
  trained on Talema. Review/edit its transcript and press Send. Browser recognition
  may send audio to its vendor. Typing is the reliable input path today.

## Implementation and limits

`dialogue.py` sends every book (the core and the six field volumes, about 98k tokens) and the last 24 history
messages with a tutor persona to the Responses API.

**Prompt caching.** The persona and books form the `instructions`, which never change, so they are a stable prompt
prefix; only the conversation in `input` varies. OpenAI caches that prefix automatically. `prompt_cache_key` (a
hash of the books) routes every turn to the same cache, and `TALEMA_CACHE_RETENTION=24h` keeps it for a day
instead of minutes. Measured with GPT-5.4 Mini: first turn 97,759 input tokens, 0 cached; next turn 97,536 of
97,759 cached (99.8%). Cached tokens are billed at the discounted cached-input rate and are faster. Each reply
reports `usage.input_tokens` and `usage.cached_tokens`. The API is stateless, so the text still travels with each
request; caching saves the reprocessing and most of the cost. Avoiding resending it would need `store: true`
with `previous_response_id`, which keeps conversations on OpenAI's servers.

**Models and rate limits.** The model is `TALEMA_MODEL`; reasoning effort is fixed at low. `gpt-5.4-mini`,
`gpt-5.6-luna` and `gpt-6-luna` all accept the nested-tree schema, the cache key and 24h retention (tested live).
A model's tokens-per-minute limit counts the ~98k book tokens on every turn even when they are cached: at the
200,000 TPM limit this project saw for `gpt-6-luna`, that is about two turns a minute. A short rate limit
(Retry-After up to 30 s) is waited out once before the turn fails; raise the limit or use a model with a higher
one for faster conversation. It requests one to three nested sentence trees
(each node a native root with its dependents nested inside it), plus translations and expression. Because the
dependents are nested, the child count cannot be wrong: the server counts them, adds each ending, and validates
the sentence; it allows one repair retry. Loans are intentionally excluded from generated
speech for now. Valid syntax does not guarantee correct meaning or captions.
History lives only in the browser tab; refreshing loses it.

`tts.py` produces WAV and phoneme-derived mouth cues. Timings are model predictions,
normalized to waveform duration, not independently measured forced alignment.
The short utterance limit keeps raw phonemes below Kokoro's 510-character limit.
`character.js` renders the face locally without another avatar service or subscription.
`/api/respond` accepts `{talema, history, start}`; `/api/utterance` accepts `{talema}`
and returns base64 WAV, cues, provider and voice. `/api/audio` retains raw WAV output.
Agents can use the same JSON routes. `/api/health` distinguishes model configuration
from TTS package availability; it does not prove API access or downloaded voice readiness.

This remains a loopback development server: no authentication, streaming model/audio,
Talema ASR, persistent student model, or production hosting controls. Full-book requests
and CPU synthesis can add noticeable latency. Live model quality must be evaluated
with real lessons; the automated tests mock API responses.

## Checks

```sh
uv run --extra tts python -m unittest discover -s avatar/tests -v
node --check avatar/public/app.js
node --check avatar/public/character.js
```

The Responses JSON schema interface was checked against the
[official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
