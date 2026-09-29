"""Does giving the vowel names only when asked keep questions about letters working, without the leak?

The persona used to list the five vowel names (vanam ... vunam) and gloss its format example ("Four is two and two").
Replies then brought them up unprompted: "Hello." answered with "The first vowel is called vanam." (about 3% of
replies in the experiments). Three arms are asked the same prompts:

  old   the persona as it was, names listed up front;
  bare  the names taken out altogether, with nothing in their place;
  new   the names taken out of the persona and appended after the books only when the learner has been asking
        about letters (dialogue.letter_note), which is what the tutor now does.

The prompts are

  - prompts that leaked in the experiments (a greeting, a comment, a doubt, a bare "Why?"), where any mention of a
    vowel is the leak, and
  - real questions about a letter, which must still work (a valid reply, ideally naming the vowel with the book's word).

The arms are rebuilt from the current persona by swapping the two passages, so they differ in nothing else. The
learner writes English (the app's "I write in" option), and there is no history, so each prompt stands alone.

    python avatar/experiments/persona_probe.py [--samples 3]

It spends on the OpenAI key in .env, about 100k input tokens a call (mostly cached), paced to the rate limit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "avatar"))
import dialogue  # noqa: E402  (reads .env)

PAUSE = 28
LEAK = re.compile(r"vowel|vanam|venam|vinam|vonam|vunam|four is two|two and two", re.I)
VOWEL_WORD = re.compile(r"\bv[aeiou]nam[aeiou]*\b")           # vanam, venam ... as spoken (with an ending)

NEW_LETTERS = ("A written letter is not a root either, so it can never be spoken. Only when the learner asks about a letter\n"
               "or a sound, use the word the book gives that vowel (you are given the words then), and put the letter in the\n"
               "caption, not in `root`. Otherwise never bring up letters, vowels or their names.\n")
BARE_LETTERS = NEW_LETTERS.replace("(you are given the words then)", "(its grammar chapter names each one)")
OLD_LETTERS = ("A written letter is not a root either, so it can never be spoken. When the learner asks about a letter or\n"
               "a sound, name the vowel with the word the book gives it: the first vowel is `vanam`, the second `venam`,\n"
               "the third `vinam`, the fourth `vonam`, the fifth `vunam`. Put the letter in the caption, not in `root`.\n")
NEW_EXAMPLE = "Use only established roots. Example: `bi fura pe si tova tova .` is\n"
OLD_EXAMPLE = "Use only established roots. Example: `bi fura pe si tova tova .` (\"Four is two and two\") is\n"

LEAK_PRONE = ["Hello.", "I enjoy this book.", "I do not understand this sentence.", "Why?"]
LETTERS = ["What is the first vowel?", "Please say the letter a.", "How do I say the vowel o?"]


def replaced(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"expected exactly one occurrence of: {old[:60]!r}"
    return text.replace(old, new)


def personas() -> dict[str, str]:
    current = dialogue.PERSONA
    previous = replaced(replaced(current, NEW_LETTERS, OLD_LETTERS), NEW_EXAMPLE, OLD_EXAMPLE)
    return {"old": previous, "bare": replaced(current, NEW_LETTERS, BARE_LETTERS), "new": current}


def ask(name: str, persona: str, message: str) -> dict:
    saved = (dialogue.PERSONA, dialogue.CACHE_KEY, dialogue.asks_about_letters)
    dialogue.PERSONA = persona
    dialogue.CACHE_KEY = "probe-" + name + str(abs(hash(persona)) % 10**8)
    if name != "new":                                     # only the current design appends the note
        dialogue.asks_about_letters = lambda message, history: False
    try:
        return dialogue.reply(message, [], False, "english")
    finally:
        dialogue.PERSONA, dialogue.CACHE_KEY, dialogue.asks_about_letters = saved


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=int, default=3, help="samples of each leak-prone prompt")
    ap.add_argument("--letter-samples", type=int, default=2, help="samples of each question about a letter")
    ap.add_argument("--arms", default="old,bare,new", help="comma-separated subset of old, bare, new")
    ap.add_argument("--out", type=Path, default=HERE / "results" / "persona_probe.json")
    args = ap.parse_args()
    who = personas()
    arms = args.arms.split(",")
    limit = {"leak-prone": args.samples, "letter": args.letter_samples}
    calls = [(kind, prompt, s, name) for s in range(max(limit.values())) for kind, prompts in (("leak-prone", LEAK_PRONE), ("letter", LETTERS))
             for prompt in prompts for name in arms if s < limit[kind]]
    counter = {"n": 0}
    real_post = dialogue.post

    def counting_post(payload):
        counter["n"] += 1
        return real_post(payload)
    dialogue.post = counting_post
    done = json.loads(args.out.read_text()) if args.out.exists() else []
    seen = {(r["kind"], r["prompt"], r["sample"], r["persona"]) for r in done}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for kind, prompt, sample, name in calls:
        if (kind, prompt, sample, name) in seen:
            continue
        counter["n"] = 0
        record = {"kind": kind, "prompt": prompt, "sample": sample, "persona": name}
        try:
            data = ask(name, who[name], prompt)
            record.update(ok=True, en=data["en"], talema=data["talema"], leak=bool(LEAK.search(data["en"])),
                          names_the_vowel=bool(VOWEL_WORD.search(data["talema"])))
        except RuntimeError as exc:
            record.update(ok=False, error=str(exc)[:160])
        record["api_calls"] = counter["n"]
        done.append(record)
        args.out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        print(f"{kind:<10} {name:<4} {prompt[:36]:<36} {'ok' if record['ok'] else 'FAILED':<7} calls={counter['n']}  "
              f"{(record.get('en') or record.get('error'))[:70]}", flush=True)
        time.sleep(PAUSE)
    print("done:", args.out)


if __name__ == "__main__":
    main()
