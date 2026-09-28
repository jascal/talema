"""Local Talema TTS adapters.

Kokoro receives IPA-like phoneme strings directly. eSpeak NG receives the same
string in its bracketed phoneme-input form and is kept as a correctness/debug
backend. Both imports and the executable are optional so the avatar can still
run without a model installed.
"""
from __future__ import annotations

import base64
import io
import os
import re
import shutil
import subprocess
import threading
import warnings
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IPA_LEXICON = ROOT / "speech" / "talema-ipa.pls"
_NS = "{http://www.w3.org/2005/01/pronunciation-lexicon}"

def _load_lexicon() -> dict[str, str]:
    tree = ET.parse(IPA_LEXICON)
    return {
        entry.findtext(f"{_NS}grapheme", "").lower(): entry.findtext(f"{_NS}phoneme", "")
        for entry in tree.findall(f"{_NS}lexeme")
    }

IPA = _load_lexicon()
_KOKORO_PIPELINE = None
_KOKORO_LOCK = threading.Lock()

TOKEN = re.compile(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ0-9]+)?|[0-9]+|[^\w\s]")
WORD = re.compile(r"[A-Za-zÀ-ÿ0-9]+(?:-[A-Za-zÀ-ÿ0-9]+)?")

def _word_phonemes(token: str) -> str:
    """Render one Talema word to IPA, using the lexicon where present."""
    key = token.lower()
    if key in IPA:
        return IPA[key]
    if re.fullmatch(r"[A-Za-zÀ-ÿ]+", token):
        # Talema's ordinary roots are simple CV spellings and stress their
        # first vowel. This fallback is intentionally transparent.
        chars = token.lower().replace("c", "k").replace("j", "y")
        chars = chars.replace("x", "ks").replace("q", "k")
        first_vowel = next((i for i, c in enumerate(chars) if c in "aeiou"), None)
        if first_vowel is not None:
            chars = ("ˈ" if first_vowel < len(chars.rstrip("aeiou")) else "") + chars
        chars = chars.replace("r", "ɾ").replace("g", "ɡ")
        return chars
    if token.isdigit():
        return token
    return token

def tokens(text: str) -> list[str]:
    """Split a Talema sentence into word, number and punctuation tokens.

    One tokenizer serves phonemization, the word list and the highlight spans, so the
    subtitle can never disagree with what is actually spoken.
    """
    return TOKEN.findall(text)

def is_word(token: str) -> bool:
    """True for a token spoken as a word (letters/digits, optionally hyphenated)."""
    return WORD.fullmatch(token) is not None

def talema_to_ipa(text: str) -> str:
    """Convert Talema words using the checked-in IPA lexicon.

    Unknown words are rendered conservatively from their spelling so literal
    names and newly coined roots remain speakable. The explicit lexicon wins.
    """
    return " ".join(_word_phonemes(token) for token in tokens(text))

def talema_words(text: str) -> list[str]:
    """The spoken word tokens, in order, excluding punctuation."""
    return [token for token in tokens(text) if is_word(token)]

def word_spans(token_list: list[str], vocab) -> list[tuple[int, int]]:
    """Map each word token onto its span in the *vocab-filtered* phoneme stream.

    The model only ever sees characters present in ``vocab``, so spans must be walked
    token by token over that same filtered stream. Two things beyond a plain count
    matter, and both shift every later word if missed:

    * Digits and other unsupported symbols are dropped, so a word the model never
      voices must not advance the cursor.
    * ``talema_to_ipa`` joins tokens with a space, and **Kokoro's vocabulary contains
      the space character**, so each gap is itself a phoneme the model receives. The
      cursor has to step over it exactly as the model does.
    """
    spans: list[tuple[int, int]] = []
    cursor = 0
    gap = 1 if ' ' in vocab else 0
    for index, token in enumerate(token_list):
        if index:
            cursor += gap
        produced = sum(1 for char in _word_phonemes(token) if char in vocab)
        if is_word(token):
            spans.append((cursor, cursor + produced))
        cursor += produced
    return spans

def _kokoro(phonemes: str, token_list: list[str] | None = None):
    global _KOKORO_PIPELINE
    from scipy.io import wavfile  # type: ignore

    with _KOKORO_LOCK:
        if _KOKORO_PIPELINE is None:
            # Kokoro and torch currently emit expected startup deprecation and
            # optional-GPU warnings. Keep those out of the avatar's console.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, module=r"torch")
                warnings.filterwarnings("ignore", category=FutureWarning, module=r"torch")
                from kokoro import KPipeline  # type: ignore
                _KOKORO_PIPELINE = KPipeline(
                    # Italian is the closest stock Kokoro voice to Talema's
                    # five-vowel inventory and tap-like intervocalic r.
                    lang_code=os.getenv("TALEMA_KOKORO_LANG", "i"),
                    repo_id=os.getenv("TALEMA_KOKORO_REPO_ID", "hexgrad/Kokoro-82M"),
                )
        pipeline = _KOKORO_PIPELINE
        voice = os.getenv("TALEMA_KOKORO_VOICE", "if_sara")
        result = next(pipeline.generate_from_tokens(tokens=phonemes, voice=voice, speed=0.92))
        samples = result.audio.cpu().numpy()
        vocab = pipeline.model.vocab
        phones = [p for p in phonemes if p in vocab]
        durations = result.pred_dur.tolist()
        spans = word_spans(token_list, vocab) if token_list else []
    stream = io.BytesIO()
    wavfile.write(stream, 24000, samples)
    cues, word_cues = cues_from_durations(phones, durations, len(samples) / 24000, spans)
    return stream.getvalue(), cues, word_cues


def cues_from_durations(phones, durations, duration, spans=None):
    """Per-phoneme mouth cues and, when word spans are given, per-word highlight cues.

    Model durations are 40 Hz frames with start/end padding. They are normalized to
    the actual waveform length so cues never drift past the audio.
    """
    if len(durations) != len(phones) + 2:
        raise RuntimeError("Kokoro timing does not match phonemes")
    scale = duration / sum(durations)
    cursor = durations[0] * scale
    cues = []
    for phone, frames in zip(phones, durations[1:-1]):
        end = cursor + frames * scale
        shape = ('closed' if phone in 'pbm' else 'round' if phone in 'ouɔʊw'
                 else 'wide' if phone in 'eiɛɪ' else 'open' if phone in 'aɑæ'
                 else 'teeth' if phone in 'fv' else 'rest' if phone in ' .,!?;:ˈˌ'
                 else 'small')
        cues.append({'start': cursor, 'end': end, 'shape': shape})
        cursor = end
    word_cues: list[dict[str, float]] = []
    if spans:
        word_cues = _spans_to_word_cues(spans, cues)
    return cues, word_cues


def _spans_to_word_cues(spans, phoneme_cues: list[dict]) -> list[dict]:
    """Turn (start, end) phoneme indices into per-word time ranges.

    A word the model did not voice (every character fell outside the vocabulary) gets a
    zero-width cue where it would have begun, so the subtitle still advances in step.
    """
    if not phoneme_cues:
        return [{'start': 0.0, 'end': 0.0} for _ in spans]
    last = len(phoneme_cues) - 1
    word_cues: list[dict] = []
    for start, end in spans:
        if end <= start:
            at = phoneme_cues[min(max(start, 0), last)]['start']
            word_cues.append({'start': at, 'end': at})
        else:
            first = min(max(start, 0), last)
            stop = min(max(end, start + 1), len(phoneme_cues)) - 1
            word_cues.append({'start': phoneme_cues[first]['start'],
                              'end': phoneme_cues[stop]['end']})
    return word_cues


def _wav_bytes_from_kokoro(phonemes):
    return _kokoro(phonemes)[0]


def utterance(text):
    if os.getenv('TALEMA_TTS', 'kokoro').lower() != 'kokoro':
        raise ValueError('The animated character currently requires Kokoro timing')
    phonemes = talema_to_ipa(text)
    token_list = tokens(text)
    audio, cues, word_cues = _kokoro(phonemes, token_list)
    return {'audio': base64.b64encode(audio).decode('ascii'), 'cues': cues,
            'words': [token for token in token_list if is_word(token)],
            'word_cues': word_cues,
            'provider': 'kokoro', 'voice': os.getenv('TALEMA_KOKORO_VOICE', 'if_sara')}

def _wav_bytes_from_espeak(phonemes: str) -> bytes:
    executable = shutil.which(os.getenv("TALEMA_ESPEAK_BIN", "espeak-ng"))
    if not executable:
        raise RuntimeError("eSpeak NG is not installed")
    # eSpeak NG's [[...]] input is phoneme mode; output stays WAV so the
    # browser does not need a platform-specific audio decoder.
    process = subprocess.run(
        [executable, "-q", "-v", os.getenv("TALEMA_ESPEAK_VOICE", "en-us"), "--stdout"],
        input=f"[[{phonemes}]]".encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.decode("utf-8", "replace") or "eSpeak NG failed")
    return process.stdout

def synthesize(text: str, provider: str | None = None) -> tuple[bytes, str, str]:
    provider = (provider or os.getenv("TALEMA_TTS", "kokoro")).lower()
    phonemes = talema_to_ipa(text)
    if provider == "kokoro":
        return _wav_bytes_from_kokoro(phonemes), provider, phonemes
    if provider in {"espeak", "espeak-ng"}:
        return _wav_bytes_from_espeak(phonemes), "espeak-ng", phonemes
    raise ValueError(f"unknown TTS provider: {provider}")

def available() -> dict[str, bool]:
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module=r"torch")
            warnings.filterwarnings("ignore", category=FutureWarning, module=r"torch")
            import kokoro  # noqa: F401
        kokoro_ok = True
    except ImportError:
        kokoro_ok = False
    return {"kokoro": kokoro_ok, "espeak-ng": shutil.which(os.getenv("TALEMA_ESPEAK_BIN", "espeak-ng")) is not None}
