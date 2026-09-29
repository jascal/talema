"""Does the conversation volume, or a looser prompt, change how Luma talks?

A 2x2, run on the real tutor (dialogue.reply) with the same scripted learner turns in every cell:

                          current prompt      loosened prompt
    books without play         A                   C
    books with the play        B                   D

"books without the play" are the books as they were on main before the volume (read from git). The loosened
prompt makes three changes, each answering a constraint of the current one: a reply need not end in a question
(a new `react` turn type), a brief acknowledgement is allowed, and small words are encouraged. It leaves the
rule against claiming feelings or experiences alone.

    python avatar/experiments/conversation_ab.py run  [--base-ref main] [--out results/ab.json]
    python avatar/experiments/conversation_ab.py show results/ab.json

The first run (results/ab.json) used --base-ref aa0b0ca, the last commit on main before the volume. Once the volume
is merged, `main` is no longer a valid baseline and `run` refuses it.

`run` spends on the OpenAI key in .env: 9 calls per cell (one opening and eight learner turns), with pauses to
stay under the model's tokens-per-minute limit, since every call carries the whole book. It writes after every
call and resumes if interrupted.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "avatar"))
import dialogue  # noqa: E402  (reads .env)

LM_SAE = Path(os.environ.get("LM_SAE", Path.home() / "code" / "lm-sae"))   # the Talema-tree compiler, to write the learner's turns
PAUSE = 36                                          # seconds between calls: ~100k tokens each against 200k per minute

# The learner speaks Talema too. Fixed turns, so the cells differ only in the tutor.
LEARNER = [
    ("I am glad.", ["(be glad (SUBJ I))"]),
    ("I want a book.", ["(want (OBJ (book a)) (SUBJ I))"]),
    ("Is this book good?", ["(whether (be good (SUBJ (book this))))"]),
    ("I do not know.", ["(know (OBJ it) not (SUBJ I))"]),
    ("Maybe I read it.", ["(read (OBJ it) maybe (SUBJ I))"]),
    ("Why?", ["(why)"]),
    ("Sorry. I do not know this word.", ["(sorry/INTJ)", "(know (OBJ (word this)) not (SUBJ I))"]),
    ("Thanks. Goodbye.", ["(thanks/NOUN)", "(goodbye/NOUN)"]),
]


def learner_turns() -> list[dict]:
    sys.path.insert(0, str(LM_SAE / "scripts" / "conlang"))
    import author
    lex, out = author.Lex(), []
    for english, trees in LEARNER:
        sentences = []
        for text in trees:
            words = [w for tree in author.parse_trees(text, "learner") for w in author.spell(lex, tree, "learner")]
            sentences.append(" ".join(words) + " .")
        talema = " ".join(sentences)
        dialogue.validate_speech(talema)
        out.append({"en": english, "talema": talema})
    return out


# ── the four cells ──────────────────────────────────────────────────────────────────────────────
def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def books_at(ref: str) -> str:
    """The books exactly as dialogue.py assembles them, but as they were at `ref`."""
    files = ["books/BUKE_DE_LORE_FIRA.md"] + sorted(
        f for f in git("ls-tree", "-r", "--name-only", ref, "books/volumes").split() if f.endswith(".md"))
    return "".join(f"\n\n=== {f} ===\n\n" + git("show", f"{ref}:{f}") for f in files)


def replaced(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"expected exactly one occurrence of: {old[:70]!r}"
    return text.replace(old, new)


def loosened(persona: str) -> str:
    p = persona
    p = replaced(p, "Use warm, natural turn-taking. Be a curious conversation partner, not a dictionary or quiz machine.\n",
                 "Use warm, natural turn-taking. Be a curious conversation partner, not a dictionary or quiz machine.\n"
                 "Talk like a person talking, not like a lesson: where a person would, use the small words the books give\n"
                 "you (hello, please, thanks, sorry, oh, ah, well, maybe, really, yes, okay).\n")
    p = replaced(p, "Do not echo their words as a standalone sentence or repeat a topic name just to fill space.\n",
                 "A brief acknowledgement of what they said (a small word such as oh, yes, well, okay, or a short reaction)\n"
                 "is natural; repeating their sentence back is not.\n")
    p = replaced(p, "Make each sentence add new information; do not paraphrase the same claim in adjacent sentences.\n",
                 "A sentence may be a small reaction or a single word; it need not add new information.\n")
    p = replaced(p, "Every reply must invite the learner to continue, and the `turn_move` field must say which:\n",
                 "The `turn_move` field says what kind of turn this is. It is metadata, never spoken:\n")
    p = replaced(p, "`offer_topic`: add one concrete, interesting example connected to the learner's interest and invite their reaction.\n",
                 "`offer_topic`: add one concrete, interesting example connected to the learner's interest and invite their reaction;\n"
                 "`react`: respond the way a person would, with no question at all.\n"
                 "Do not end every reply with a question. Ask one only when a person would. Often the natural turn is to\n"
                 "answer, react, agree, disagree, joke, thank, apologise or say goodbye, and let the learner speak.\n")
    return p


def cells(base_ref: str) -> dict[str, dict]:
    persona, schema = dialogue.PERSONA, dialogue.SCHEMA
    loose_schema = copy.deepcopy(schema)
    loose_schema["properties"]["turn_move"]["enum"] = [*schema["properties"]["turn_move"]["enum"], "react"]
    without, with_play = books_at(base_ref), dialogue.BOOK
    assert "volumes/talk.md" not in without, (
        f"--base-ref {base_ref!r} already has the conversation volume; pass a commit from before it was added")
    made = {}
    for name, (label, book, p, s) in {
        "A": ("no play, current prompt", without, persona, schema),
        "B": ("play, current prompt", with_play, persona, schema),
        "C": ("no play, loosened prompt", without, loosened(persona), loose_schema),
        "D": ("play, loosened prompt", with_play, loosened(persona), loose_schema),
    }.items():
        made[name] = {"label": label, "book": book, "persona": p, "schema": s,
                      "key": "ab-" + hashlib.sha256((p + book).encode()).hexdigest()[:16]}
    return made


def call(cell: dict, message: str, history: list[dict], start: bool, counter: dict) -> dict:
    """One tutor turn with the cell's books, prompt and schema swapped in."""
    saved = (dialogue.PERSONA, dialogue.BOOK, dialogue.CACHE_KEY, dialogue.SCHEMA)
    dialogue.PERSONA, dialogue.BOOK, dialogue.CACHE_KEY, dialogue.SCHEMA = (
        cell["persona"], cell["book"], cell["key"], cell["schema"])
    try:
        return dialogue.reply(message, history, start)
    finally:
        dialogue.PERSONA, dialogue.BOOK, dialogue.CACHE_KEY, dialogue.SCHEMA = saved


def run(base_ref: str, out: Path) -> None:
    turns = learner_turns()
    made = cells(base_ref)
    print("learner turns:", *[f"\n  {t['en']!r:<38} {t['talema']}" for t in turns])
    for name, c in made.items():
        print(f"cell {name}: {c['label']:<26} books {len(c['book']):,} chars, prompt {len(c['persona']):,} chars")
    counter = {"n": 0}
    real_post = dialogue.post

    def counting_post(payload):
        counter["n"] += 1
        return real_post(payload)
    dialogue.post = counting_post

    done = json.loads(out.read_text()) if out.exists() else []
    seen = {(r["cell"], r["round"]) for r in done}
    history = {name: [] for name in made}
    for r in sorted(done, key=lambda r: r["round"]):                # rebuild each cell's history when resuming
        if r.get("data"):
            history[r["cell"]] += [{"role": "user", "content": r["sent"]}, {"role": "assistant", "content": r["data"]["talema"]}]
    out.parent.mkdir(parents=True, exist_ok=True)
    for rnd in range(len(turns) + 1):                                # round 0 is the opening; then the learner turns
        for name, cell in made.items():
            if (name, rnd) in seen:
                continue
            start = rnd == 0
            message = "" if start else turns[rnd - 1]["talema"]
            record = {"cell": name, "round": rnd, "learner": None if start else turns[rnd - 1],
                      "sent": "Begin a beginner lesson." if start else message}
            for attempt in range(4):
                counter["n"] = 0
                began = time.time()
                try:
                    record["data"] = call(cell, message, history[name][-24:], start, counter)
                    record.pop("error", None)
                    break
                except RuntimeError as exc:
                    record["error"] = str(exc)
                    if "rate limit" in str(exc).lower() and attempt < 3:
                        time.sleep(65)
                        continue
                    break
            record["api_calls"], record["seconds"] = counter["n"], round(time.time() - began, 1)
            if record.get("data"):
                history[name] += [{"role": "user", "content": record["sent"]},
                                  {"role": "assistant", "content": record["data"]["talema"]}]
            done.append(record)
            out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
            state = record["data"]["talema"][:60] if record.get("data") else "FAILED " + record["error"][:80]
            print(f"round {rnd} cell {name}: {record['api_calls']} call(s), {record['seconds']}s  {state}", flush=True)
            time.sleep(PAUSE)
    print("done:", out)


# ── reading the results ─────────────────────────────────────────────────────────────────────────
def lexicon_sets():
    rows = [json.loads(line) for line in (ROOT / "data" / "lexicon.jsonl").read_text().splitlines()]
    gloss: dict[str, set] = {}
    for r in rows:
        for w in r["en"].split("|"):
            gloss.setdefault(w.strip().lower(), set()).add(r["root"])

    def roots(*words):
        return set().union(*(gloss.get(w, set()) for w in words))
    intj = {r["root"] for r in rows if r["cls"] == "INTJ"}
    small = intj | roots("well", "maybe", "perhaps", "really", "actually", "indeed", "please", "thanks", "thank", "sorry",
                         "pardon", "yes", "okay", "sure", "welcome", "goodbye", "hello")
    ask = roots("what", "who", "why", "how", "where", "when", "which", "whether")
    return small, ask


def parse(talema: str, small: set, ask: set) -> list[dict]:
    out = []
    for sentence in [s.strip() for s in talema.split(".") if s.strip()]:
        roots = []
        for w in sentence.split():
            m = re.fullmatch(r"(.*[^aeiou])([aeiou]+)", w)
            roots.append(m[1] if m else w)
        out.append({"words": len(roots), "small": sum(r in small for r in roots), "question": any(r in ask for r in roots)})
    return out


def show(path: Path) -> None:
    results = json.loads(path.read_text())
    small, ask = lexicon_sets()
    names = sorted({r["cell"] for r in results})
    labels = {r["cell"]: r for r in results}
    print(f"{len(results)} tutor turns in {path.name}\n")
    print(f"{'cell':<5}{'ok':>4}{'calls':>7}{'sent/reply':>12}{'words/sent':>12}{'small words':>13}{'opens small':>13}{'ends ask':>10}{'any ask':>9}   turn_move")
    for name in names:
        rs = [r for r in results if r["cell"] == name and r["round"] > 0]
        good = [r for r in rs if r.get("data")]
        parsed = [parse(r["data"]["talema"], small, ask) for r in good]
        nsent = sum(len(p) for p in parsed) or 1
        nwords = sum(s["words"] for p in parsed for s in p) or 1
        first_small = sum(1 for p in parsed if p and p[0]["small"] and p[0]["words"] <= 3)
        ends_ask = sum(1 for p in parsed if p and p[-1]["question"])
        any_ask = sum(1 for p in parsed if any(s["question"] for s in p))
        moves = {}
        for r in good:
            moves[r["data"]["turn_move"]] = moves.get(r["data"]["turn_move"], 0) + 1
        calls = sum(r["api_calls"] for r in results if r["cell"] == name)
        n = len(good) or 1
        print(f"{name:<5}{len(good):>2}/{len(rs)}{calls:>7}{nsent / n:>12.2f}{nwords / nsent:>12.2f}"
              f"{sum(s['small'] for p in parsed for s in p) / nwords:>12.1%}{first_small:>9}/{len(good):<3}"
              f"{ends_ask:>6}/{len(good):<3}{any_ask:>5}/{len(good):<3}   {moves}")
    print()
    for rnd in range(len(LEARNER) + 1):
        heads = [r for r in results if r["round"] == rnd]
        if not heads:
            continue
        learner = heads[0]["learner"]
        print(f"=== round {rnd}: " + (f"learner says {learner['en']!r}  [{learner['talema']}]" if learner else "the tutor opens"))
        for name in names:
            r = next((r for r in heads if r["cell"] == name), None)
            if r is None:
                continue
            if not r.get("data"):
                print(f"  {name}  FAILED: {r['error'][:110]}")
                continue
            d = r["data"]
            print(f"  {name}  [{d['turn_move']:<12} {d['emotion']:<11}] {d['en']}")
            print(f"      {d['talema']}")
    print()
    tin = sum(r["data"]["usage"]["input_tokens"] for r in results if r.get("data"))
    cached = sum(r["data"]["usage"]["cached_tokens"] for r in results if r.get("data"))
    print(f"input tokens over all turns: {tin:,} ({cached:,} cached)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--base-ref", default="main", help="git ref of the books without the play")
    r.add_argument("--out", type=Path, default=HERE / "results" / "ab.json")
    s = sub.add_parser("show")
    s.add_argument("path", type=Path)
    args = ap.parse_args()
    run(args.base_ref, args.out) if args.cmd == "run" else show(args.path)
