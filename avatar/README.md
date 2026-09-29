# Talema avatar

Luma is a photograph of a (fictional) person that moves in real time, with an LLM tutor and
local Kokoro speech. Spoken and written dialogue stays in Talema; English, Spanish and German
captions are separate. Her mouth follows the phoneme durations Kokoro predicts, and she blinks,
looks up while she thinks, breathes, and shows the tutor's mood in her brows. It is one still
photograph plus a few small edited patches of it, composited in the browser: not generated video,
not a 3D model, and nothing is generated while you talk. See [Luma's face](#lumas-face).

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
separately from a ChatGPT subscription; conversation turns and every book are
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
- **I write in** (beside the message box) chooses the language you write to Luma in. *Talema* is the default and the
  real test: she has to read what you write and answer. *English* takes reading out of it: she reads your English
  and still answers only in Talema, so what you see is her answer alone. It is how to tell a stiff reply from a
  misread one, and it is the same switch the experiment in `avatar/experiments/` uses, so what that measures is what
  the app does. The choice is remembered by the browser, applies from your next message, and changes one sentence of
  her instructions (`dialogue.persona_for`) and the cache key. Suggestion buttons and the starter chips show, and
  send, English when you write English; the microphone then listens for English.
- After each model reply, Luma offers two or three context-aware Talema utterances as buttons, each with a translation in the selected caption language. Clicking one sends that phrase as the learner's next turn; without model configuration, the offline greeting has no generated suggestions.
- The opening asks which topic the learner wants. Later turns should stay with the learner's
  stated interest, answer their actual point, and ask a specific follow-up or offer a related
  example; they should not repeat broad topic-selection questions or greetings.
- The tutor is prompted to remember recent turns, acknowledge intent, recast mistakes,
  simplify after confusion, and offer one useful next step. These are prompted
  behaviors, not a claim of evaluated teaching competence.
- **Stop** cancels pending browser requests and pauses speech. You can interrupt with
  another message. A request already submitted to the model may still finish/bill.
  <kbd>Esc</kbd> also stops, from anywhere on the page.
- Audio controls pause/replay/seek; mouth movement follows the audio clock.
- Captions switch independently and are never synthesized. The live Talema subtitle
  highlights the word Luma is currently saying, derived from the TTS phoneme cues.
  Each bubble keeps its own **↻ Replay** button so you can hear a turn again
  without re-asking the tutor.
- After each reply the status line shows the model and voice, plus the prompt-cache
  hit ratio (`NN% cached (X/Y tokens)`) so the cost savings are visible.
- Microphone input uses browser recognition: an Italian locale when you write Talema, which is not
  trained on Talema, and an English one when you write English. Review/edit its transcript and press Send. Browser recognition
  may send audio to its vendor. Typing is the reliable input path today.

## Implementation and limits

`dialogue.py` sends every book (the core and every field volume; about 98k tokens when this was measured, before the food and conversation volumes, which add roughly 6k) and the last 24 history
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

**Rejecting a bad root.** A whole word in the `root` field (`buke` for `buk`) is repaired silently by
peeling the ending. A bare vowel cannot be: `a` `e` `i` `o` `u` are endings, not roots, and no root in the
lexicon is a bare vowel, so peeling leaves nothing. That is the one mistake that reaches the model again,
and the retry names it directly — it is told which value was wrong, that it is an ending counting
dependents, and the table (`a` 0, `e` 1, `i` 2, `o` 3, `u` 4, `ea` 5).

The commonest cause is a learner asking about a letter ("say the letter a"). The model is right about the
intent and wrong about the form: a written letter is not a root, so it can never be spoken. The retry
looks up the word the book gives that vowel and hands it over — *use `vanam` in that node, and put the
letter in the caption* — resolved from the lexicon rather than hardcoded, so it stays right if a root is
ever renamed. Asking about a letter also makes the server append the five names after the books
(`dialogue.letter_note`, for that turn and the two after it), so the retry is usually not needed. The names are
not in the persona: listed there they surfaced unprompted, about 3% of replies ("Hello." answered with "The
first vowel is called vanam."), and appending after the books leaves the cached prefix the same every turn. If a reply
still fails twice, nothing is spoken and the status line says so: the server will not substitute a
sentence it could not validate, because wrong Talema is worse than no Talema. Press **Stop** and send
again, or start a new lesson.

**Captions that add content.** A caption must translate the speech, never extend it. Three shapes are
caught, each measured against `data/sentences.jsonl` before being adopted.

*An invented sentence.* This is the tutor's standing habit, and the cheapest to catch: Talema is compact,
so it feels obliged to pay the learner back in English. "Hi. What topic do you want?" (two Talema
sentences) came back as *"Hello! You can greet me with 'hello.' Which topic would you like to explore?"*
— three, one of them never spoken. 1,549 of the 1,553 published captions have exactly as many sentences
as the Talema they translate and **none has fewer**, so the invariant is free. The four exceptions are
the same habit already in print: `bove bi fura pe si tova tova .` is one sentence, but its English adds
*"We have a proof."* The count ignores the book's claim markers (`Proved:`, `Seen:`, `Open:`) and slash
alternatives.

*Enumeration.* The tutor says "five vowels", then writes "Talema has five vowels: a, e, i, o, and u",
listing something it never said. The check is a caption that both outgrows the speech and enumerates
literal letters; it matches none of the book's captions, so the dictionary lines, which do legitimately
enumerate, still pass.

*Order.* The tutor asks "which vowel", then writes "which would you like to look at next". A caption may
not use an order word unless the speech carries the order. The surface forms for all three caption
languages are read from the lexicon's own `de` and `es` columns — English *first*, Spanish *primero*,
*cuarto*, *último*, German *erste*, *vierte*, *fünfte*, *nächste* — so none of them can slip past the
check, and a new gloss stays covered without touching the code. German and Spanish inflect, so their
forms also match on a stem plus a short ending (*Nächstes*); English is matched exactly, because
stem matching would read "**aga**inst" as "again". A caption word is satisfied by any root that carries
the order (first is `fir`, `fis` or `rimer`), and a coined root carries its order in its own English
gloss: `vonam` is glossed "vowel-fourth", so saying `vonama` really does convey "fourth". On the corpus
this flags 0.13% of the English and German captions and none of the Spanish, and the flags are genuine
errors in the published book rather than false alarms — "This is the fourth rule" is spelled
`bi ruli fura la`, using the *cardinal* four, not the ordinal.

All three are narrow by design. They catch the shapes that recur; they do not prove a caption is right,
and a caption can still be wrong without inventing a sentence, enumerating, or implying order. The
persona carries the real weight: one sentence per sentence, no sentence of its own, be concrete rather
than categorical, and if a sentence is worth saying, say it in Talema.

**Naming a letter.** Each vowel has a spoken name, coined as a root (`vanam` `venam` `vinam` `vonam`
`vunam` — the name of the first…fifth vowel) and written into the core book beside the written-letter
notation. So `kari vanama vokele fira .` ("vanam is the name of the first vowel") is a valid sentence
the avatar can speak and the exact parser can round-trip. The book still writes the letters as the
hyphenated gloss `a-a`; that is deliberate notation for a grammar chapter and `validate_speech` still
rejects it, because a written letter is not a Talema tree. Naming a vowel by position is what makes it
sayable: the letter itself has no root — `a` `e` `i` `o` `u` are bare vowels and cannot be a node — while
the ordinals (`fir` `sed` `tit` `kuret` `finat`) already existed. The rest of the sound discussion was
always speakable: `let` letter, `vokel` vowel, `sonid` sound, `nam` name, `deg` order.

`tts.py` produces WAV, phoneme-derived mouth cues, and per-word highlight cues
aggregated from those phonemes. Timings are model predictions, normalized to
waveform duration, not independently measured forced alignment.
Word spans are walked over the same vocabulary-filtered phoneme stream the model
receives, so a word the model does not voice (a digit, say) and the periods between
sentences do not push the highlight out of step.
The short utterance limit keeps raw phonemes below Kokoro's 510-character limit.
`character.js` renders the face locally, in the browser, without another avatar service or
subscription. `/api/respond` accepts `{talema, history, start, language}` (`talema` is the learner's message, in Talema or, with
`language: "english"`, in English; `/api/health` lists the `input_languages`); `/api/utterance` accepts `{talema}`
and returns base64 WAV, cues, words and word cues, provider and voice. `/api/audio`
retains raw WAV output. Agents can use the same JSON routes. `/api/health`
distinguishes model configuration from TTS package availability; it does not prove
API access or downloaded voice readiness.

This remains a loopback development server: no authentication, streaming model/audio,
Talema ASR, persistent student model, or production hosting controls. Full-book requests
and CPU synthesis can add noticeable latency. Live model quality must be evaluated
with real lessons; the automated tests mock API responses.

## Luma's face

`avatar/public/portrait/` holds one 1536×1152 photograph (`base.webp`), ten small patches of it, and a
brow map: 390 KiB in all. `character.js` (WebGL2) composites them; `face.js` decides how much of each is
visible and has no browser dependencies, so it is unit-tested in Node.

| part | how it moves |
|---|---|
| mouth | six patches (`closed round wide open teeth small`) for what `tts.py` emits, plus `smile` for the *encouraging* mood. The cue under the playhead picks one. |
| eyes | patches for `blink`, half-shut `lids` and a look up (`gaze_up`, used while she thinks) |
| brows | **not patches**: the shader moves the brow and the skin above it a few pixels, from a map measured off the photo (`brows.webp`). Mood sets how far: *curious* lifts one, *thoughtful* lowers and draws them in, *encouraging* lifts both. |
| head | small tilt, sway and breath on a shared warp, so every patch moves with it and the shoulders stay planted |

Every patch is a masked edit of the *same* photograph, so the person, lighting and skin texture stay the
same and only the masked region changes; the patch fades to nothing at its rim, so it has no edge. The
mouth region is a polygon that follows the face (a rectangle wide enough to reach the smile lines also
touches the hair at the jaw), and the model is told to relax or deepen the smile lines with each shape.

Each choice below answers something that looked wrong, so it is worth knowing before changing it:

- **Patches are conversational, not full-strength.** The model's first "ah" was a wide-jawed yawn and its
  "ee" a grin; blended at partial weight they only ghost two lip outlines, so the shapes are regenerated at
  the amplitude of relaxed speech and shown at full weight.
- **Mouth shapes move at a constant speed** (`MOUTH_MOVE`, 60 ms), not an exponential ease. Easing has a
  long tail, so at a cue every 75 ms the two or three mouths before this one were all still faintly visible:
  lips from words ago over the current shape. A shape that has been left is now gone exactly.
- **Eyes and brows never dissolve slowly.** Fading one eye photo into another shows two irises until it
  finishes, and an exponential ease made that half a second. Gaze is a 120 ms smoothstep, about a saccade.
- **Brows are a warp, not patches.** A patch can only dissolve one brow into another, which shows two
  brows while it lasts, and a patch that misses part of the original leaves it showing. The pull is
  measured from the photo because the right brow's arch droops down to the lashes; it stops at the brow's
  own lower edge, tapers at the outer tail, and fades over as much of the gap to the lashes as there is,
  so the eyelid skin is not stretched.
- **Nothing moves with speech energy.** Brows that lift on every syllable read as flashing. There is no
  idle side-glance either: it read as a tic.
- The composite is `Σ wᵢ·imageᵢ` (each patch drawn at `wₖ / (w_photo + w₁ + … + wₖ)`), which the tests
  check equals the weighted sum whatever the drawing order.

**Provenance.** The person is synthetic: generated with `gpt-image-2.5-sunburst` from the prompt in
`tools/portrait.py`, then edited with the same model. She is not a real person and not a likeness of one.
Regenerating means spending on the Images API with your `OPENAI_API_KEY`: the base portrait plus ten
edits was a few dozen calls in all, counting retries. The browser never calls it.

**Rebuilding.** The committed assets are what ship. `tools/portrait.py` documents and reproduces them, but
its inputs (the full-frame generations, about 28 MB) are not committed; they are kept, git-ignored, in
`avatar/tools/raw/`. **`base.png` there is the only source of "the same person": editing from anything
else, including the lossy `base.webp`, would not match the photo.** To change a mouth shape, regenerate
just that one against the same base; to change a region or the feathering, no API is needed:

```sh
# needs Pillow and numpy only; no API key
uv run --no-project --with pillow --with numpy python avatar/tools/portrait.py build --raw avatar/tools/raw
# regenerate one variant (uses OPENAI_API_KEY from .env); the tool flags an implausible result
uv run --no-project --with pillow --with numpy python avatar/tools/portrait.py edit --raw avatar/tools/raw open
```

**Limits.** One fixed pose: the head tilts a couple of degrees but does not turn, and the hair only moves
with the head. Eyes look forward, blink, or look up-right; nothing else. Between two mouth shapes there is a
brief cross-dissolve (about 60 ms), so fast speech blends neighbouring lips. Without WebGL2 she is shown as
the still photo. `prefers-reduced-motion` calms the head, not the lips. Realism ends where a still
photograph does: she will not read as video of a real person for long.

## Checks

```sh
uv run --extra tts python -m unittest discover -s avatar/tests -v
node --test avatar/tests/face.test.js
node --check avatar/public/app.js
node --check avatar/public/face.js
node --check avatar/public/character.js
```

The image-decoding tests in `test_portrait.py` (patch sizes, rims, the brow map) skip without Pillow and
numpy; run them with `uv run --no-project --with pillow --with numpy python -m unittest discover -s avatar/tests`.

The Responses JSON schema interface was checked against the
[official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
