"""Independent meaning review of the authored pairs (PREREG_TRANSFER_LADDER.md section 5; P5).

The author of the pairs is a Claude model. The reader here is an OpenAI model, a different family, and it is BLIND to
the intended English: it sees only the Talema tree (each word with its class and English meaning, dependents indented
under their head) and writes the English it expresses. A second call, without the tree, compares that reading with the
intended English. Only "same" items survive; everything else is dropped, not repaired. Resumable: results are appended
to review/reviews.jsonl and skipped on rerun.

    research/.venv/bin/python research/benchmark/review.py [--limit N] [--workers 6]

Spends on the OpenAI key in .env: two short calls per item (no book), so ~2,900 calls for the full pool.
"""
import argparse
import concurrent.futures as futures
import json
import sys
import time
from pathlib import Path

import bench

sys.path.insert(0, str(bench.TALEMA / "avatar"))
import dialogue  # noqa: E402  (reads .env)

HERE = Path(__file__).parent
OUT = HERE / "review" / "reviews.jsonl"
OUT_V2 = HERE / "review" / "reviews_whether_v2.jsonl"       # rerun of the whether-rooted items with the corrected rubric
OUT_REORDER = HERE / "review" / "reviews_reorder.jsonl"     # rerun of the items whose dependents were reordered (Amendment 4)
MODEL = "gpt-5.4-mini"        # a different family from the author; the same cheap model the conversation judge uses
SHOTS = ["Please give me the bread.", "What do you see?", "I think it is not good.", "I will see you tomorrow."]
SHOTS_V2 = SHOTS + ["Do you want a story?"]

READ_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["english"],
               "properties": {"english": {"type": "string"}}}
COMPARE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["same", "difference"],
                  "properties": {"same": {"type": "boolean"}, "difference": {"type": "string"}}}

READ_RUBRIC = (
    "Below is one sentence of a constructed language, shown as a tree. Each line is a word: its root, its class and its "
    "English meaning. A word's dependents are indented beneath it and come after it. The words <subject>, <object> and "
    "<to-whom> mark the word beneath them as the subject, the object or the person addressed or given to. "
    "Write the ordinary English sentence the tree expresses, the way a fluent speaker would say it. Do not add content "
    "the tree lacks and do not drop content it has. Output JSON.")
READ_RUBRIC_V2 = READ_RUBRIC.replace(
    "Output JSON.",
    "A sentence whose top word is 'whether' is a yes/no question: write it as a direct question, not as a 'whether' clause. "
    "Output JSON.")
COMPARE_RUBRIC = (
    "Two English sentences. A is what an author meant. B is a reader's rendering of a tree in a constructed language. "
    "Do they express the same meaning? They must have the same participants in the same roles, the same polarity "
    "(negation), the same sentence type (statement, question or request), and the same content words. Differences of "
    "article, tense or plain synonymy are fine ('may' and 'maybe', 'shop' and 'store'); an added, missing or changed "
    "content word, a swapped subject and object, a lost negation, or a question read as a statement is a difference. "
    "Output JSON: same (true or false) and, if false, the difference in a few words.")


def render(tree, depth=0):
    root, kids = tree[0], tree[1:]
    cls, en = bench.LEX.roots.get(root, ("?", root, "", "", ""))[:2]
    line = "  " * depth + f"{root}  [{cls}]  {en.split('|')[0]}"
    return "\n".join([line] + [render(k, depth + 1) for k in kids])


def shots(wanted=None):
    rows = [json.loads(l) for l in (bench.TALEMA / "data" / "sentences.jsonl").read_text().splitlines()]
    out = []
    for want in (wanted or SHOTS):
        row = next(r for r in rows if r["en"] == want and r["talema"].endswith("."))
        out.append((render(bench.decode(row["talema"][:-1].strip())), want))
    return out


def ask(prompt, schema, name):
    payload = {"model": MODEL, "store": False, "input": prompt, "max_output_tokens": 500, "reasoning": {"effort": "low"},
               "text": {"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}}}
    for attempt in range(4):
        try:
            res = dialogue.post(payload)
            text = "".join(c.get("text", "") for i in res.get("output", []) if i.get("type") == "message" for c in i.get("content", []))
            return json.loads(text)
        except (RuntimeError, ValueError, KeyError):
            time.sleep(4 * (attempt + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--whether-v2", action="store_true",
                    help="rerun only the items whose tree is rooted at 'whether' with the corrected rubric (writes reviews_whether_v2.jsonl)")
    ap.add_argument("--ids-file", type=Path, help="review only these ids, with the corrected rubric (writes reviews_reorder.jsonl)")
    args = ap.parse_args()
    out_path, rubric, wanted = (OUT_V2, READ_RUBRIC_V2, SHOTS_V2) if args.whether_v2 else (OUT, READ_RUBRIC, SHOTS)
    if args.ids_file:
        out_path, rubric, wanted = OUT_REORDER, READ_RUBRIC_V2, SHOTS_V2
    files = ["dev", "test", "exposed_dev", "exposed_test"]
    items = [json.loads(l) for name in files if (HERE / "pool" / f"{name}.jsonl").exists()
             for l in (HERE / "pool" / f"{name}.jsonl").read_text().splitlines()]
    OUT.parent.mkdir(exist_ok=True)
    if args.whether_v2:
        items = [it for it in items if it["native_tree"][0] == bench.LEX.resolve("whether", "review")[0]]
    if args.ids_file:
        keep = set(args.ids_file.read_text().split())
        items = [it for it in items if it["id"] in keep]
    done = {json.loads(l)["id"] for l in out_path.read_text().splitlines()} if out_path.exists() else set()
    todo = [it for it in items if it["id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    examples = "\n\n".join(f"Tree:\n{t}\nEnglish: {e}" for t, e in shots(wanted))

    def one(it):
        tree = render(tuple(json.loads(json.dumps(it["native_tree"]))) if False else _tuple(it["native_tree"]))
        read = ask(f"{rubric}\n\nExamples:\n\n{examples}\n\nNow this one.\nTree:\n{tree}\nEnglish:", READ_SCHEMA, "reading")
        if not read:
            return {"id": it["id"], "set": it["set"], "error": "read failed"}
        cmp_ = ask(f"{COMPARE_RUBRIC}\n\nA: {it['english']}\nB: {read['english']}", COMPARE_SCHEMA, "comparison")
        if not cmp_:
            return {"id": it["id"], "set": it["set"], "error": "compare failed"}
        return {"id": it["id"], "set": it["set"], "intended": it["english"], "reader": read["english"], **cmp_}

    with futures.ThreadPoolExecutor(args.workers) as pool, out_path.open("a") as f:
        for n, rec in enumerate(pool.map(one, todo), 1):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if n % 50 == 0 or n == len(todo):
                print(f"reviewed {n}/{len(todo)}", flush=True)


def _tuple(t):
    return tuple([t[0]] + [_tuple(k) for k in t[1:]])


if __name__ == "__main__":
    main()
