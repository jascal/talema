"""R2 (reading, learner errors): mechanical perturbations of well-formed items, each verified by the exact parser (P5).

Categories (PREREG_TRANSFER_LADDER.md section 5):
  valid           the item unchanged; gold = the parser accepts it
  structural      a word's arity ending changed, a word deleted, or a word inserted; gold = the parser rejects it
  unknown-root    one content root replaced by a well-formed root the lexicon does not have; gold = the parser accepts
                  the sentence and warns UNKNOWN_ROOT at that word
  meaning-change  the subject and object particles swapped, or two different leaves swapped; gold = the parser accepts it
                  (the sentence is grammatical and now says something else)
A system is asked whether the text is well-formed Talema and, if not, where the fault is. Gold is always the parser's
own verdict. Locations are token indexes (0-based over the whitespace-separated words, the final '.' included). For a
structural error the accepted locations are the edited token and the token the parser's offset falls in.
"""
import random
import re

import bench

CONS = "ptkbdgmnlrsfvh"
VOWELS = "aeiou"


def split_ending(word):
    m = re.fullmatch(r"(.*[^aeiou])([aeiou]+)", word)
    return (m[1], m[2]) if m else (word, "")


def numeral_value(ending):
    v = 0
    for ch in ending:
        v = v * 5 + VOWELS.index(ch)
    return v


def token_of(text, char_offset):
    """The token index whose character span contains the offset, or None."""
    if char_offset is None:
        return None
    pos = 0
    for i, tok in enumerate(text.split()):
        start = text.index(tok, pos)
        end = start + len(tok)
        if start <= char_offset <= end:
            return i
        pos = end
    return None


def nonsense_root(rnd, length):
    """A well-formed root (C V C V ... C) that the lexicon does not have."""
    for _ in range(1000):
        s = "".join(rnd.choice(CONS) + rnd.choice(VOWELS) for _ in range(max(1, length - 1))) + rnd.choice(CONS)
        if s not in bench.LEX.roots:
            return s
    raise RuntimeError("no free root found")


def structural(words, rnd):
    """(new words, edit token index, kind) or None."""
    n = len(words)
    kind = rnd.choice(["arity-up", "arity-down", "delete", "insert"])
    i = rnd.randrange(n)
    if kind in ("arity-up", "arity-down"):
        root, ending = split_ending(words[i])
        v = numeral_value(ending)
        nv = v + 1 if kind == "arity-up" else v - 1
        if nv < 0 or nv > 6:
            return None
        return words[:i] + [root + bench.numeral(nv)] + words[i + 1:], i, kind
    if kind == "delete":
        leaves = [k for k, w in enumerate(words) if numeral_value(split_ending(w)[1]) == 0]
        if not leaves:
            return None
        i = rnd.choice(leaves)
        return words[:i] + words[i + 1:], i, kind
    leaves = [k for k, w in enumerate(words) if numeral_value(split_ending(w)[1]) == 0]
    if not leaves:
        return None
    j = rnd.choice(leaves)
    at = rnd.randrange(n + 1)
    return words[:at] + [words[j]] + words[at:], at, kind


def unknown_root(words, rnd):
    cands = [k for k, w in enumerate(words)
             if bench.LEX.roots.get(split_ending(w)[0], ("",))[0] in bench.CONTENT]
    if not cands:
        return None
    i = rnd.choice(cands)
    root, ending = split_ending(words[i])
    new = nonsense_root(rnd, max(2, (len(root) + 1) // 2))
    return words[:i] + [new + ending] + words[i + 1:], i, "unknown-root"


def meaning_change(words, rnd):
    subj, obj = bench.LEX.resolve("SUBJ", "r2")[0], bench.LEX.resolve("OBJ", "r2")[0]
    ps = [k for k, w in enumerate(words) if split_ending(w)[0] == subj]
    ts = [k for k, w in enumerate(words) if split_ending(w)[0] == obj]
    if ps and ts:
        a, b = ps[0], ts[0]
        out = list(words)
        out[a], out[b] = out[b], out[a]
        return out, a, "swap-subject-object"
    leaves = [k for k, w in enumerate(words) if numeral_value(split_ending(w)[1]) == 0]
    pairs = [(a, b) for a in leaves for b in leaves if a < b and words[a] != words[b]]
    if not pairs:
        return None
    a, b = rnd.choice(pairs)
    out = list(words)
    out[a], out[b] = out[b], out[a]
    return out, a, "swap-leaves"


BUILDERS = {"structural": structural, "unknown-root": unknown_root, "meaning-change": meaning_change}


def build(items, n_valid, n_each, rnd):
    """items: pool items (dicts with id, talema). Returns R2 item dicts (text, category, base_id, edit, gold)."""
    items = list(items)
    rnd.shuffle(items)
    valid, rest = items[:n_valid], items[n_valid:]
    out = [{"category": "valid", "base_id": it["id"], "text": it["talema"], "edit": None} for it in valid]
    cursor = 0
    for category, builder in BUILDERS.items():
        made = 0
        while made < n_each and cursor < len(rest):
            it = rest[cursor]; cursor += 1
            words = it["talema"].split()[:-1]
            got = builder(words, rnd)
            if not got:
                continue
            new_words, index, kind = got
            text = " ".join(new_words) + " ."
            if text == it["talema"]:
                continue
            out.append({"category": category, "base_id": it["id"], "text": text, "edit": {"kind": kind, "token_index": index}})
            made += 1
    return out


def label(entries):
    """Attach the exact parser's verdict; drop perturbations whose verdict does not match their category."""
    verdicts = bench.parse_with_node([e["text"] for e in entries])
    kept = []
    for e, v in zip(entries, verdicts):
        cat = e["category"]
        if cat == "valid" or cat == "meaning-change":
            if not v["ok"] or v.get("unknown"):
                continue
            e["gold"] = {"verdict": "valid"}
        elif cat == "structural":
            if v["ok"]:
                continue
            loc = token_of(e["text"], v["error"].get("start"))
            accepted = sorted({e["edit"]["token_index"], *([loc] if loc is not None else [])})
            e["gold"] = {"verdict": "error", "code": v["error"]["code"], "parser_token": loc, "accepted_tokens": accepted}
        else:                                           # unknown-root
            if not v["ok"] or len(v.get("unknown_nodes", [])) != 1:
                continue
            idx = token_of(e["text"], v["unknown_nodes"][0]["start"])
            if idx != e["edit"]["token_index"]:
                continue
            e["gold"] = {"verdict": "warning", "code": "UNKNOWN_ROOT", "accepted_tokens": [idx]}
        kept.append(e)
    return kept
