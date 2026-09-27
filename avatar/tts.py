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

def talema_to_ipa(text: str) -> str:
    """Convert Talema words using the checked-in IPA lexicon.

    Unknown words are rendered conservatively from their spelling so literal
    names and newly coined roots remain speakable. The explicit lexicon wins.
    """
    tokens = re.findall(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ0-9]+)?|[0-9]+|[^\w\s]", text)
    output: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in IPA:
            output.append(IPA[key])
            continue
        if re.fullmatch(r"[A-Za-zÀ-ÿ]+", token):
            # Talema's ordinary roots are simple CV spellings and stress their
            # first vowel. This fallback is intentionally transparent.
            chars = token.lower().replace("c", "k").replace("j", "y")
            chars = chars.replace("x", "ks").replace("q", "k")
            first_vowel = next((i for i, c in enumerate(chars) if c in "aeiou"), None)
            if first_vowel is not None:
                chars = ("ˈ" if first_vowel < len(chars.rstrip("aeiou")) else "") + chars
            chars = chars.replace("r", "ɾ").replace("g", "ɡ")
            output.append(chars)
        elif token.isdigit():
            output.append(token)
        else:
            output.append(token)
    return " ".join(output)

def _kokoro(phonemes: str):
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
        phones = [p for p in phonemes if p in pipeline.model.vocab]
        durations = result.pred_dur.tolist()
    stream = io.BytesIO()
    wavfile.write(stream, 24000, samples)
    return stream.getvalue(), cues_from_durations(phones, durations, len(samples) / 24000)


def cues_from_durations(phones, durations, duration):
    if len(durations) != len(phones) + 2:
        raise RuntimeError("Kokoro timing does not match phonemes")
    # Model durations are 40 Hz frames, including start/end padding.
    # Normalize to the actual generated waveform length to avoid end drift.
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
    return cues


def _wav_bytes_from_kokoro(phonemes):
    return _kokoro(phonemes)[0]


def utterance(text):
    if os.getenv('TALEMA_TTS', 'kokoro').lower() != 'kokoro':
        raise ValueError('The animated character currently requires Kokoro timing')
    phonemes = talema_to_ipa(text)
    audio, cues = _kokoro(phonemes)
    return {'audio': base64.b64encode(audio).decode('ascii'), 'cues': cues,
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
