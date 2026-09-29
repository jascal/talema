"""Does the conversation volume, or a looser prompt, change how Luma talks?

Runs the real tutor (dialogue.reply) on fixed learner turns, in five cells:

    A  books without the play    current prompt
    B  books with the play       current prompt
    C  books without the play    loosened prompt
    D  books with the play       loosened prompt
    E  books with the play       loosened prompt + a line pointing at the play

"Books without the play" are the books as they were at --base-ref, read from git. The loosened prompt makes three
changes, each answering a constraint of the current one: a reply need not end in a question (a new `react` turn
type), a brief acknowledgement is allowed, and small words are encouraged. It leaves the rule against claiming
feelings or experiences alone. Cell E adds one sentence telling her the last volume is a play and to talk like it.

There are three scripted conversations of eight learner turns each (after the tutor's opening), about different
things and deliberately unlike the play's market, so the test measures generalisation and not remembered lines.

By default the learner writes Talema, so the tutor must first read it. With --learner english the learner writes the
same turns in English (and every cell's prompt gets one sentence saying so), which removes comprehension from the test:
what is left is what she says back. It is the same switch as the app's "I write in" control (dialogue.reply's
`language`), so the experiment tests exactly what the UI does.

    python avatar/experiments/conversation_ab.py run   [--base-ref REF] [--out results/ab2.json] [--learner english]
    python avatar/experiments/conversation_ab.py compare results/ab2.json results/ab3_english.json
    python avatar/experiments/conversation_ab.py judge results/ab2.json
    python avatar/experiments/conversation_ab.py show  results/ab2.json      (also reads ab2.judged.json)

`run` spends on the OpenAI key in .env: 9 tutor calls per cell per conversation, paced to stay under the model's
tokens-per-minute limit since every call carries the whole book. `judge` makes small calls to a cheaper model that
rates each reply blind (it is never told the cell) for fit and naturalness. Both write after every call and resume.

The first run (results/ab.json, one conversation, four cells) used --base-ref aa0b0ca, the last commit on main before
the volume. Once the volume is merged, `main` is no longer a valid baseline and `run` refuses it.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import copy
import hashlib
import json
import os
import random
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
PAUSE = 28                                          # seconds between tutor calls: ~105k tokens each against 200k per minute
JUDGE_MODEL = "gpt-5.4-mini"

# The learner speaks Talema too. Fixed turns, so the cells differ only in the tutor.
CONVERSATIONS = [
    {"name": "a bad day", "turns": [
        ("My day is bad.", ["(be bad (SUBJ (day my)))"]),
        ("I lose my book.", ["(lose (OBJ (book my)) (SUBJ I))"]),
        ("Can you help me?", ["(whether (can (OBJ (help (OBJ I) (SUBJ you))) (SUBJ you)))"]),
        ("I do not have money.", ["(have (OBJ (money no)) (SUBJ I))"]),
        ("Maybe I am wrong.", ["(be wrong maybe (SUBJ I))"]),
        ("Why do you help me?", ["(help (OBJ I) why (SUBJ you))"]),
        ("You are kind.", ["(be kind/ADJ (SUBJ you))"]),
        ("Thank you. Goodbye.", ["(thank (OBJ you) (SUBJ I))", "(goodbye/NOUN)"]),
    ]},
    {"name": "doubt while learning", "turns": [
        ("I enjoy this book.", ["(enjoy (OBJ (book this)) (SUBJ I))"]),
        ("It is difficult.", ["(be difficult (SUBJ it))"]),
        ("I do not understand this sentence.", ["(understand (OBJ (sentence this)) not (SUBJ I))"]),
        ("Please say it again.", ["(please (say (OBJ it) again/ADV))"]),
        ("Now I understand.", ["(understand (OBJ it) now (SUBJ I))"]),
        ("Is this right?", ["(whether (be right (SUBJ this)))"]),
        ("I think I know more now.", ["(think (OBJ (know (OBJ more) now (SUBJ I))) (SUBJ I))"]),
        ("Thanks for your help. I will see you tomorrow.",
         ["(thanks/NOUN (for (help/NOUN your)))", "(see/VERB (OBJ you) tomorrow/NOUN will (SUBJ I))"]),
    ]},
    {"name": "small talk", "turns": [
        ("Hello.", ["(hello/INTJ)"]),
        ("I have a sister.", ["(have (OBJ (sister a)) (SUBJ I))"]),
        ("She lives far away.", ["(live/VERB far/ADV (SUBJ she))"]),
        ("Do you have a sister?", ["(whether (have (OBJ (sister a)) (SUBJ you)))"]),
        ("I think sisters are good.", ["(think (OBJ (be good (SUBJ (sister every)))) (SUBJ I))"]),
        ("But she is angry with me.", ["(but (be angry (with I) (SUBJ she)))"]),
        ("Ha! It is a joke.", ["(ha/INTJ)", "(be (joke/NOUN a) (SUBJ it))"]),
        ("I go now. Goodbye.", ["(go now (SUBJ I))", "(goodbye/NOUN)"]),
    ]},
]


def compile_conversations() -> list[dict]:
    sys.path.insert(0, str(LM_SAE / "scripts" / "conlang"))
    import author
    lex, out = author.Lex(), []
    for conv in CONVERSATIONS:
        turns = []
        for english, trees in conv["turns"]:
            sentences = []
            for text in trees:
                words = [w for tree in author.parse_trees(text, "learner") for w in author.spell(lex, tree, "learner")]
                sentences.append(" ".join(words) + " .")
            talema = " ".join(sentences)
            dialogue.validate_speech(talema)
            turns.append({"en": english, "talema": talema})
        out.append({"name": conv["name"], "turns": turns})
    return out


def in_the_play() -> set[str]:
    """Talema sentences that occur in the play, to flag learner turns that repeat it word for word."""
    path = ROOT / "data" / "sentences.jsonl"
    return {json.loads(line)["talema"] for line in path.read_text().splitlines() if '"id": "talk/' in line}


# ── the cells ───────────────────────────────────────────────────────────────────────────────────
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


SMALL_WORDS = ("you (hello, please, thanks, sorry, oh, ah, well, maybe, really, yes, okay).\n")
POINTER = ("The last volume, the book of conversation, is a play. In it people answer what was just said, give a reason\n"
           "after a why, and often reply with only a word or two. Talk like them.\n")


def loosened(persona: str, pointer: bool = False) -> str:
    p = persona
    p = replaced(p, "Use warm, natural turn-taking. Be a curious conversation partner, not a dictionary or quiz machine.\n",
                 "Use warm, natural turn-taking. Be a curious conversation partner, not a dictionary or quiz machine.\n"
                 "Talk like a person talking, not like a lesson: where a person would, use the small words the books give\n"
                 + SMALL_WORDS + (POINTER if pointer else ""))
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
    assert "volumes/talk.md" in with_play, "the books the tutor loads do not include the conversation volume"
    made = {}
    for name, (label, book, p, s) in {
        "A": ("no play, current prompt", without, persona, schema),
        "B": ("play, current prompt", with_play, persona, schema),
        "C": ("no play, loosened prompt", without, loosened(persona), loose_schema),
        "D": ("play, loosened prompt", with_play, loosened(persona), loose_schema),
        "E": ("play, loosened + pointer", with_play, loosened(persona, pointer=True), loose_schema),
    }.items():
        made[name] = {"label": label, "book": book, "persona": p, "schema": s,
                      "key": "ab-" + hashlib.sha256((p + book).encode()).hexdigest()[:16]}
    return made


def call(cell: dict, message: str, history: list[dict], start: bool, language: str) -> dict:
    """One tutor turn with the cell's books, prompt and schema swapped in. `language` is what the app's
    "I write in" control sends, so the experiment and the UI share one code path."""
    saved = (dialogue.PERSONA, dialogue.BOOK, dialogue.CACHE_KEY, dialogue.SCHEMA)
    dialogue.PERSONA, dialogue.BOOK, dialogue.CACHE_KEY, dialogue.SCHEMA = (
        cell["persona"], cell["book"], cell["key"], cell["schema"])
    try:
        return dialogue.reply(message, history, start, language)
    finally:
        dialogue.PERSONA, dialogue.BOOK, dialogue.CACHE_KEY, dialogue.SCHEMA = saved


def run(base_ref: str, out: Path, learner: str = "talema") -> None:
    convs = compile_conversations()
    made = cells(base_ref)
    print("the learner writes:", learner)
    play = in_the_play()
    print("cells:")
    for name, c in made.items():
        print(f"  {name}  {c['label']:<26} books {len(c['book']):,} chars, prompt {len(c['persona']):,} chars")
    for i, conv in enumerate(convs):
        print(f"conversation {i}: {conv['name']}")
        for t in conv["turns"]:
            repeated = [s for s in t["talema"].split(" . ") if (s.strip(" .") + " .") in play]
            print(f"  {t['en']:<48} {t['talema']}" + ("   [word for word in the play]" if repeated else ""))
    counter = {"n": 0}
    real_post = dialogue.post

    def counting_post(payload):
        counter["n"] += 1
        return real_post(payload)
    dialogue.post = counting_post

    done = json.loads(out.read_text()) if out.exists() else []
    seen = {(r["conv"], r["cell"], r["round"]) for r in done}
    history = {(ci, name): [] for ci in range(len(convs)) for name in made}
    for r in sorted(done, key=lambda r: r["round"]):                 # rebuild each history when resuming
        if r.get("data"):
            history[(r["conv"], r["cell"])] += [{"role": "user", "content": r["sent"]},
                                                {"role": "assistant", "content": r["data"]["talema"]}]
    out.parent.mkdir(parents=True, exist_ok=True)
    for ci, conv in enumerate(convs):
        for rnd in range(len(conv["turns"]) + 1):                    # round 0 is the opening
            for name, cell in made.items():
                if (ci, name, rnd) in seen:
                    continue
                start = rnd == 0
                turn = None if start else conv["turns"][rnd - 1]
                message = "" if start else turn["en" if learner == "english" else "talema"]
                record = {"conv": ci, "cell": name, "round": rnd, "learner": turn, "language": learner,
                          "sent": "Begin a beginner lesson." if start else message}
                for attempt in range(4):
                    counter["n"] = 0
                    began = time.time()
                    try:
                        record["data"] = call(cell, message, history[(ci, name)][-24:], start, learner)
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
                    history[(ci, name)] += [{"role": "user", "content": record["sent"]},
                                            {"role": "assistant", "content": record["data"]["talema"]}]
                done.append(record)
                out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
                state = record["data"]["talema"][:56] if record.get("data") else "FAILED " + record["error"][:70]
                print(f"conv {ci} round {rnd} cell {name}: {record['api_calls']} call(s), {record['seconds']}s  {state}", flush=True)
                time.sleep(PAUSE)
    print("done:", out)


# ── the judge ───────────────────────────────────────────────────────────────────────────────────
JUDGE_SCHEMA = {"type": "object", "properties": {
    "fit": {"type": "integer", "minimum": 1, "maximum": 5},
    "natural": {"type": "integer", "minimum": 1, "maximum": 5},
    "forced_question": {"type": "boolean"},
    "caption_off": {"type": "boolean"},
    "note": {"type": "string"}},
    "required": ["fit", "natural", "forced_question", "caption_off", "note"], "additionalProperties": False}

RUBRIC = """You are rating ONE reply from a conversation partner called Luma, who speaks only a small constructed
language (Talema). You see her English rendering and a word-by-word gloss of what she actually said. Rate only the
reply, given what the learner just said.

fit (1-5): how well the reply answers or reacts to what the learner just said. 5 = exactly what an attentive person
would say next (a feeling gets a reaction, a question gets an answer, thanks is acknowledged, goodbye gets a
goodbye, a mistake or doubt is met kindly). 3 = related but generic, or slightly off. 1 = irrelevant, contradicts what
was said, or ignores it.

natural (1-5): does it sound like a person talking, as opposed to a lesson or a quiz? 5 = varied, as short as a person
would be, no needless question, no parroting. 1 = stiff: an interview or quiz pattern, a question that a person would
not ask, repeating the learner's words back, or lecturing.

forced_question: true if the reply ends with a question that a person would not have asked there.
caption_off: true if the English rendering and the gloss disagree materially; if so, rate by the gloss.
Do not reward length. Do not judge the Talema's grammar. note: at most 20 words."""


def gloss_of(talema: str, table: dict[str, str]) -> str:
    out = []
    for w in talema.replace(".", " . ").split():
        if w == ".":
            out.append("|")
            continue
        m = re.fullmatch(r"(.*[^aeiou])([aeiou]+)", w)
        out.append(table.get(m[1], m[1]) if m else w)
    return " ".join(out)


def gloss_table() -> dict[str, str]:
    rows = [json.loads(line) for line in (ROOT / "data" / "lexicon.jsonl").read_text().splitlines()]
    return {r["root"]: r["en"].split("|")[0] or r["root"] for r in rows}


def judge(path: Path, passes: int = 2) -> None:
    results = json.loads(path.read_text())
    table = gloss_table()
    out = path.with_suffix(".judged.json")
    judged = json.loads(out.read_text()) if out.exists() else []
    seen = {(j["conv"], j["cell"], j["round"], j["pass"]) for j in judged}
    by = {(r["conv"], r["cell"], r["round"]): r for r in results}
    jobs = []
    for p in range(passes):
        items = [r for r in results if r.get("data") and r["round"] > 0 and (r["conv"], r["cell"], r["round"], p) not in seen]
        random.Random(1000 + p).shuffle(items)                       # blind, and a different order each pass
        jobs += [(r, p) for r in items]

    def one(job):
        r, p = job
        lines = []
        for k in range(1, r["round"]):                               # the conversation so far, in English
            before = by.get((r["conv"], r["cell"], k))
            if before and before.get("data"):
                lines += [f"Learner: {before['learner']['en']}", f"Luma: {before['data']['en']}"]
        d = r["data"]
        prompt = (RUBRIC + "\n\nConversation so far:\n" + ("\n".join(lines) or "(none)") +
                  f"\n\nThe learner just said: {r['learner']['en']}\n\nLuma's reply:\n  English rendering: {d['en']}\n"
                  f"  Word-by-word gloss: {gloss_of(d['talema'], table)}")
        payload = {"model": JUDGE_MODEL, "store": False, "input": prompt, "max_output_tokens": 600,
                   "reasoning": {"effort": "low"},
                   "text": {"format": {"type": "json_schema", "name": "rating", "strict": True, "schema": JUDGE_SCHEMA}}}
        for attempt in range(3):
            try:
                res = dialogue.post(payload)
                text = "".join(c.get("text", "") for i in res.get("output", []) if i.get("type") == "message" for c in i.get("content", []))
                rating = json.loads(text)
                return {"conv": r["conv"], "cell": r["cell"], "round": r["round"], "pass": p, **rating}
            except (RuntimeError, ValueError, KeyError):
                time.sleep(5 * (attempt + 1))
        return None

    with futures.ThreadPoolExecutor(4) as pool:
        for n, result in enumerate(pool.map(one, jobs), 1):
            if result:
                judged.append(result)
            if n % 20 == 0 or n == len(jobs):
                out.write_text(json.dumps(judged, ensure_ascii=False, indent=1))
                print(f"judged {n}/{len(jobs)}", flush=True)
    out.write_text(json.dumps(judged, ensure_ascii=False, indent=1))
    print("wrote", out)


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


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return centre - half, centre + half


def boot(values: list[float], n: int = 4000, seed: int = 7) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(n))
    return sum(values) / len(values), means[int(0.025 * n)], means[int(0.975 * n)]


def show(path: Path) -> None:
    results = json.loads(path.read_text())
    for r in results:
        r.setdefault("conv", 0)
    judged_path = path.with_suffix(".judged.json")
    judged = json.loads(judged_path.read_text()) if judged_path.exists() else []
    small, ask = lexicon_sets()
    names = sorted({r["cell"] for r in results})
    per: dict[tuple, dict] = {}                                      # (conv, cell, round) -> per-reply measures
    for r in results:
        if r["round"] == 0 or not r.get("data"):
            continue
        p = parse(r["data"]["talema"], small, ask)
        words = sum(s["words"] for s in p) or 1
        per[(r["conv"], r["cell"], r["round"])] = {
            "ends_ask": float(bool(p and p[-1]["question"])), "any_ask": float(any(s["question"] for s in p)),
            "small": sum(s["small"] for s in p) / words, "opens_small": float(bool(p and p[0]["small"] and p[0]["words"] <= 3)),
            "sentences": len(p), "words_per_sentence": words / len(p) if p else 0}
    scores: dict[tuple, dict] = {}
    for j in judged:
        scores.setdefault((j["conv"], j["cell"], j["round"]), {"fit": [], "natural": [], "forced": [], "off": []})
        s = scores[(j["conv"], j["cell"], j["round"])]
        s["fit"].append(j["fit"]); s["natural"].append(j["natural"]); s["forced"].append(float(j["forced_question"])); s["off"].append(float(j["caption_off"]))
    for key, s in scores.items():
        if key in per:
            per[key].update({k: sum(v) / len(v) for k, v in s.items()})

    ncv = len({r["conv"] for r in results})
    print(f"{len(results)} tutor turns, {ncv} conversation(s), {len(judged)} judge ratings in {judged_path.name if judged else '(none)'}\n")
    head = f"{'cell':<5}{'n':>4}{'repairs':>8}{'ends on ?':>17}{'small words':>14}{'opens small':>13}{'fit':>18}{'natural':>18}"
    print(head)
    for name in names:
        items = [v for (c, cell, rnd), v in per.items() if cell == name]
        n = len(items)
        k = sum(v["ends_ask"] for v in items)
        lo, hi = wilson(int(k), n)
        opens = sum(v["opens_small"] for v in items)
        rs = [r for r in results if r["cell"] == name]
        repairs = sum(max(0, r["api_calls"] - 1) for r in rs)
        failed = sum(1 for r in rs if not r.get("data"))
        fit = boot([v["fit"] for v in items if "fit" in v]); nat = boot([v["natural"] for v in items if "natural" in v])
        fit_s = f"{fit[0]:.2f} [{fit[1]:.2f},{fit[2]:.2f}]" if judged else "-"
        nat_s = f"{nat[0]:.2f} [{nat[1]:.2f},{nat[2]:.2f}]" if judged else "-"
        print(f"{name:<5}{n:>4}{repairs:>6}/{failed}{int(k):>7}/{n:<3}({lo:.0%}-{hi:.0%}){sum(v['small'] for v in items) / n:>10.1%}"
              f"{int(opens):>9}/{n:<3}{fit_s:>19}{nat_s:>18}")
    print("\n(ends on ? = the reply's last sentence is a question; 95% Wilson intervals. fit and natural are the blind judge's 1-5,"
          " with 95% bootstrap intervals over replies.)")

    def contrast(label, a, b, metric):
        """Mean of (b - a) over the same learner turn (conversation and round), with a bootstrap interval."""
        diffs = [per[(c, b, r)][metric] - per[(c, a, r)][metric] for (c, cell, r) in per if cell == a
                 and (c, b, r) in per and metric in per[(c, a, r)] and metric in per[(c, b, r)]]
        if not diffs:
            return None
        m, lo, hi = boot(diffs)
        return f"  {label:<34}{m:>+8.2f}  [{lo:+.2f}, {hi:+.2f}]" + ("   <- excludes 0" if lo > 0 or hi < 0 else "")
    pairs = [("play, current prompt (B - A)", "A", "B"), ("play, loosened prompt (D - C)", "C", "D"),
             ("loosened prompt, no play (C - A)", "A", "C"), ("loosened prompt, with play (D - B)", "B", "D"),
             ("pointer to the play (E - D)", "D", "E")]
    for metric, title in (("ends_ask", "ends on a question"), ("small", "share of small words"), ("fit", "judge: fit"), ("natural", "judge: natural")):
        if metric in ("fit", "natural") and not judged:
            continue
        print(f"\npaired difference in {title} (same learner turn):")
        for label, a, b in pairs:
            line = contrast(label, a, b, metric)
            if line and a in names and b in names:
                print(line)

    print("\nturn types:")
    for name in names:
        moves: dict = {}
        for r in results:
            if r["cell"] == name and r.get("data") and r["round"] > 0:
                moves[r["data"]["turn_move"]] = moves.get(r["data"]["turn_move"], 0) + 1
        print(f"  {name}  {moves}")
    tin = sum(r["data"]["usage"]["input_tokens"] for r in results if r.get("data"))
    cached = sum(r["data"]["usage"]["cached_tokens"] for r in results if r.get("data"))
    print(f"\ninput tokens over all tutor turns: {tin:,} ({cached:,} cached)")


def measures(path: Path) -> dict[tuple, dict]:
    """(conv, cell, round) -> mean judged fit and natural, from a results file and its .judged.json."""
    judged = json.loads(path.with_suffix(".judged.json").read_text())
    acc: dict[tuple, dict] = {}
    for j in judged:
        a = acc.setdefault((j["conv"], j["cell"], j["round"]), {"fit": [], "natural": []})
        a["fit"].append(j["fit"]); a["natural"].append(j["natural"])
    return {k: {m: sum(v) / len(v) for m, v in d.items()} for k, d in acc.items()}


def compare(first: Path, second: Path) -> None:
    """How much better is each cell in `second` than in `first`, on the same learner turns?"""
    a, b = measures(first), measures(second)
    print(f"second minus first, paired by conversation, cell and round ({first.name} -> {second.name})\n")
    print(f"{'cell':<6}{'n':>4}{'fit':>26}{'natural':>26}")
    for cell in sorted({k[1] for k in a} & {k[1] for k in b}):
        keys = [k for k in a if k[1] == cell and k in b]
        row = []
        for metric in ("fit", "natural"):
            diffs = [b[k][metric] - a[k][metric] for k in keys]
            m, lo, hi = boot(diffs)
            row.append(f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]" + (" *" if lo > 0 or hi < 0 else "  "))
        print(f"{cell:<6}{len(keys):>4}{row[0]:>26}{row[1]:>26}")
    print("\n(* = the interval excludes 0)")


def transcript(path: Path, conv: int) -> None:
    results = [r for r in json.loads(path.read_text()) if r.get("conv", 0) == conv]
    names = sorted({r["cell"] for r in results})
    for rnd in range(0, 9):
        heads = [r for r in results if r["round"] == rnd]
        if not heads:
            continue
        learner = heads[0]["learner"]
        print(f"\n=== round {rnd}: " + (f"learner: {learner['en']!r}" if learner else "the tutor opens"))
        for name in names:
            r = next((r for r in heads if r["cell"] == name), None)
            if r and r.get("data"):
                d = r["data"]
                print(f"  {name} [{d['turn_move'][:7]:<7}] {d['en']}")
            elif r:
                print(f"  {name} FAILED: {r['error'][:90]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--base-ref", default="main", help="git ref of the books without the play")
    r.add_argument("--out", type=Path, default=HERE / "results" / "ab2.json")
    r.add_argument("--learner", choices=["talema", "english"], default="talema", help="the language the learner writes in")
    j = sub.add_parser("judge")
    j.add_argument("path", type=Path)
    j.add_argument("--passes", type=int, default=2)
    s = sub.add_parser("show")
    s.add_argument("path", type=Path)
    c = sub.add_parser("compare")
    c.add_argument("first", type=Path)
    c.add_argument("second", type=Path)
    t = sub.add_parser("transcript")
    t.add_argument("path", type=Path)
    t.add_argument("conv", type=int)
    args = ap.parse_args()
    if args.cmd == "run":
        run(args.base_ref, args.out, args.learner)
    elif args.cmd == "judge":
        judge(args.path, args.passes)
    elif args.cmd == "show":
        show(args.path)
    elif args.cmd == "compare":
        compare(args.first, args.second)
    else:
        transcript(args.path, args.conv)
