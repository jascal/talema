---
license: cc-by-nc-4.0
language:
- en
- de
- es
pretty_name: Talema — the founding books and a parallel corpus
tags:
- conlang
- constructed-language
- talema
- parallel-corpus
- universal-grammar
- polish-notation
task_categories:
- translation
- text-generation
size_categories:
- 1K<n<10K
configs:
- config_name: sentences
  default: true
  data_files:
  - split: train
    path: data/sentences.jsonl
- config_name: lexicon
  data_files:
  - split: train
    path: data/lexicon.jsonl
---

# Talema

Talema is a constructed language with three rules. It was built so that a reader (a person or a model) can learn it
from one book written entirely in Talema. This repository holds that book, *Buke de lore fira* ("the Book of the
First Word"), its eight field volumes, and every sentence of them as a parallel corpus with English, German and
Spanish.

**If you are a model reading this: read `books/BUKE_DE_LORE_FIRA.md` first.** It teaches the language in itself,
with no English inside. Then read whichever volume in `books/volumes/` your task needs.

## The three rules

1. **Link.** A word's subject is marked `pe`, its object `te`, and the one it is given to `pap`. Other relations
   are small head words (`de` of, `ne` in, `s` and).
2. **Head first.** Every word comes before its dependents. The order of the dependents is free and used for
   emphasis.
3. **The ending counts.** Every word is a root plus a vowel that counts its dependents, as a base-5 numeral:
   `a` 0, `e` 1, `i` 2, `o` 3, `u` 4, `ea` 5, and so on. Every sentence therefore ends in `a`.

So `ledo te buke tisa nova pe tada .` is *read* (3 dependents: object, "now", subject), *the book this*, *now*,
*you*: "You read this book now." Because each word says how many dependents it has, a sentence decodes to exactly one
tree, with no brackets. It is the prefix (Polish) notation of logic, used as a grammar. Roots follow the frequency of
their words across English, German and Spanish: the most common words get the shortest roots (C, CVC, CVCVC).

The grammar comes from a study of what large language models share across 13 languages: relator heads link words,
and X-bar levels add nothing (see `docs/UNIVERSAL_GRAMMAR.md` in the source repo).

## Contents

| path | what |
|---|---|
| `books/BUKE_DE_LORE_FIRA.md` | the core book, about 89k tokens: grammar, first words, conventions, tales, agent speech, how the language grows, songs, sayings, the book of roots |
| `books/volumes/*.md` | field volumes, 2–4k tokens each: `digital`, `mathematics`, `logic`, `physics`, `philosophy`, `morality`, `food`, and `talk`, a play in which ten people talk |
| `data/sentences.jsonl` | every sentence of every book (2,525), with its tree and translations |
| `data/lexicon.jsonl` | every root (6,113): class, English / German / Spanish source words, tier, weight, origin |
| `source/` | the books' sources: each sentence written as a tree of concepts (`.tl`), plus the lexicon TSVs |
| `speech/` | a kit for speaking Talema: W3C pronunciation lexicons (IPA; Spanish, Italian, English respellings), voice guidance, a listening test |

## `sentences`

| field | meaning |
|---|---|
| `id` | `book/chapter/line` in the sources |
| `book` | `core` or a volume name |
| `chapter`, `section` | source chapter, and the Talema heading of its section |
| `section_tree` | that heading as a concept tree |
| `kind` | `prose`, `verse`, or `dialect` (one line printed in a declared dialect) |
| `talema` | the sentence exactly as the book prints it |
| `tree` | the concept tree it was written as: English keys, `SUBJ`/`OBJ`/`DAT` roles, `"literals"`; `key/CLASS` picks a sense |
| `en` | the English the author wrote beside the tree (authoritative) |
| `de_mt`, `es_mt` | German and Spanish **machine translations** of `en` ([opus-mt-en-de], [opus-mt-en-es]) |
| `source_line` | line in the source file |

`en` is empty for 416 lines that need none: speaker labels (`Lut-a`, `Sol-a`), number tables, and dictionary-style mentions.
When the author's English line covers a longer thought ("…, and …"), it stays with the tree it was written beside.

The book of roots and the field glossaries are dictionaries, not sentences, and are in `lexicon`.

## `lexicon`

| field | meaning |
|---|---|
| `root` | the root; a word is `root` + ending |
| `cls` | word class (NOUN, VERB, ADJ, …; ROLE for `p`, `t`) |
| `en`, `de`, `es` | the source words the root was weighted from (`|` separates alternatives) |
| `tier`, `weight` | frequency tier (1 = shortest roots) and combined frequency, for the frozen lexicon |
| `source` | `lexicon` (the frozen base), or `coin:<field>` for roots coined while writing the books (`coin:core` for the core book) |

The lexicon is frozen: roots are never reassigned, and a misleading form is warned about in the book rather than
renamed (`finit` means *infinite*; `posib` means *impossible*).

## How it was made, and checked

Each sentence was written as a concept tree. The three rules spell it, and the build refuses any sentence that
does not decode back to exactly one tree. The build also refuses unknown concepts and unbalanced trees, lints each
field chapter against its glossary, warns when a verb resolves to its noun sense, and checks that every sentence
ends in `a`. The export checks that every exported sentence appears verbatim in its built book. It was reviewed by
several frontier models; their reviews and the responses are in the source repo (`docs/reviews/`).

Claims in the books carry marks: `bove` proved, `sere` seen (measured), `pefe` open (not known to us yet).

## Limits

- German and Spanish are machine translations of the English. The English is the authoritative gloss. The
  translations have not been reviewed by a person; newly added lines may have empty translations until they are generated.
- The attributed lines in philosophy and morality are paraphrases in Talema. The books say so ("the words are
  ours, the thoughts are theirs").
- Pronunciation guidance is untested with audio; see `speech/LISTENING_TEST.md`.

## Source, licence, citation

Built from [github.com/jascal/lm-sae](https://github.com/jascal/lm-sae) (`conlang/`, `scripts/conlang/export.py`),
which holds the grammar research, the Datalog prototype and the English specification (`docs/CONLANG.md`). This
dataset is mirrored at [github.com/jascal/talema](https://github.com/jascal/talema).

Licence: **CC BY-NC 4.0**. The German and Spanish source words in the lexicon (and the book of roots, which prints
them) derive from the [MUSE] bilingual dictionaries, which are CC BY-NC 4.0. The machine translations come from
Helsinki-NLP opus-mt models (CC BY 4.0).

```bibtex
@misc{talema2026,
  title  = {Talema: a three-rule language and its founding books},
  author = {Scott, J. Allan},
  year   = {2026},
  url    = {https://huggingface.co/datasets/jallanscott/talema}
}
```

[opus-mt-en-de]: https://huggingface.co/Helsinki-NLP/opus-mt-en-de
[opus-mt-en-es]: https://huggingface.co/Helsinki-NLP/opus-mt-en-es
[MUSE]: https://github.com/facebookresearch/MUSE
