"""The C (conversation) test set: four scripted learner conversations, written new for the test set (P5).

The three conversations in avatar/experiments/conversation_ab.py were used while the tutor was being developed, so they
are development material only. These are unrelated to them and to the play (a trip, cooking, a disagreement, weather),
each with eight learner turns (nine tutor rounds counting her opening), the learner writing in Talema or in English.

    research/.venv/bin/python research/benchmark/c_test.py     -> c_test.json
"""
import json
from pathlib import Path

import bench

CONVERSATIONS = [
    {"name": "planning a trip", "turns": [
        ("I want to go to the sea.", ["(want/VERB (OBJ (go/VERB (to/ADP (sea/NOUN the)))) (SUBJ I))"]),
        ("Do you know a good train?", ["(whether (know/VERB (OBJ (train/NOUN good/ADJ a)) (SUBJ you)))"]),
        ("The train is slow.", ["(be slow/ADJ (SUBJ (train/NOUN the)))"]),
        ("How long is the trip?", ["(be long/ADJ how (SUBJ (trip/NOUN the)))"]),
        ("I will go with my friend.", ["(go/VERB will/VERB (with (friend/NOUN my)) (SUBJ I))"]),
        ("We have two bags.", ["(have (OBJ (bag/NOUN two)) (SUBJ we))"]),
        ("The sea is beautiful.", ["(be beautiful/ADJ (SUBJ (sea/NOUN the)))"]),
        ("Thank you. I will see you tomorrow.",
         ["(thank/VERB (OBJ you) (SUBJ I))", "(see/VERB (OBJ you) tomorrow/NOUN will/VERB (SUBJ I))"]),
    ]},
    {"name": "cooking dinner", "turns": [
        ("I cook dinner today.", ["(cook/VERB (OBJ dinner/NOUN) today/NOUN (SUBJ I))"]),
        ("I have fish and bread.", ["(have (OBJ (and fish/NOUN bread/NOUN)) (SUBJ I))"]),
        ("Do you enjoy fish?", ["(whether (enjoy/VERB (OBJ fish/NOUN) (SUBJ you)))"]),
        ("I do not have cheese.", ["(have (OBJ cheese/NOUN) not (SUBJ I))"]),
        ("What do you eat every day?", ["(eat/VERB (OBJ what) (in (day/NOUN every)) (SUBJ you))"]),
        ("The fish is hot.", ["(be hot/ADJ (SUBJ (fish/NOUN the)))"]),
        ("It is good.", ["(be good/ADJ (SUBJ it))"]),
        ("Come, we eat.", ["(come/VERB)", "(eat/VERB (SUBJ we))"]),
    ]},
    {"name": "a friend who disagrees", "turns": [
        ("My friend says I am wrong.", ["(say/VERB (OBJ (be wrong/ADJ (SUBJ I))) (SUBJ (friend/NOUN my)))"]),
        ("I do not agree.", ["(agree/VERB not (SUBJ I))"]),
        ("Why does he think so?", ["(think/VERB so/ADV why (SUBJ he))"]),
        ("He is tired.", ["(be tired/ADJ (SUBJ he))"]),
        ("Maybe he is right.", ["(be right/ADJ maybe/ADV (SUBJ he))"]),
        ("I will ask him.", ["(ask/VERB will/VERB (OBJ he) (SUBJ I))"]),
        ("Is that a good idea?", ["(whether (be (idea/NOUN good/ADJ a) (SUBJ that/DET)))"]),
        ("Thanks for the talk.", ["(thanks/NOUN (for (talk/NOUN the)))"]),
    ]},
    {"name": "the weather and a plan", "turns": [
        ("The rain falls today.", ["(fall/VERB today/NOUN (SUBJ (rain/NOUN the)))"]),
        ("I do not enjoy the rain.", ["(enjoy/VERB (OBJ (rain/NOUN the)) not (SUBJ I))"]),
        ("The day is cold.", ["(be cold/ADJ (SUBJ (day/NOUN the)))"]),
        ("I have a hat.", ["(have (OBJ (hat/NOUN a)) (SUBJ I))"]),
        ("Will the rain fall tomorrow?", ["(whether (fall/VERB tomorrow/NOUN will/VERB (SUBJ (rain/NOUN the))))"]),
        ("I want to sleep.", ["(want/VERB (OBJ (sleep/VERB (SUBJ I))) (SUBJ I))"]),
        ("The night is long.", ["(be long/ADJ (SUBJ (night/NOUN the)))"]),
        ("Good night.", ["(night/NOUN good/ADJ)"]),
    ]},
]


def main():
    out, problems = [], []
    for conv in CONVERSATIONS:
        turns = []
        for english, trees in conv["turns"]:
            sentences = []
            for tree in trees:
                try:
                    c = bench.compile_tree(tree)
                except bench.ItemError as exc:
                    problems.append(f"{conv['name']}: {english}: {exc}")
                    continue
                sentences.append(c["talema"])
            talema = " ".join(sentences)
            if talema and not bench.in_domain(talema):
                problems.append(f"{conv['name']}: {english}: outside the domain")
            turns.append({"en": english, "talema": talema, "trees": trees})
        out.append({"name": conv["name"], "turns": turns})
    for p in problems:
        print("  ", p)
    if not problems:
        (Path(__file__).parent / "c_test.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print("wrote c_test.json:", len(out), "conversations,", sum(len(c["turns"]) for c in out), "learner turns")
    print(len(problems), "problem(s)")


if __name__ == "__main__":
    main()
