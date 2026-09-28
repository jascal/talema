# Talema exact parser

Written Talema already carries its parse: each word's final vowel numeral gives
its number of children, and the head precedes those children. This Worker
decodes that tree, shows lexical glosses from `data/lexicon.jsonl`, and reports
malformed trees with character offsets. Unknown native roots remain parseable and
receive a warning, because Talema permits new roots.

`POST /parse` accepts `{ "text": "bi fura pe si tova tova ." }` and returns
`sentences[].tree` and flat `sentences[].tokens`. Each node has its source
`start`/`end`, `root`, `ending`, `arity`, `head`, `relation`, and gloss. The
`relation` field identifies explicit relator words; bare dependents keep the
neutral label `dependent`. It does not claim to produce Universal Dependencies.

`POST /v1/chat/completions` accepts the existing parser spoke request shape
(`messages`, `lang: "talema"`) and returns the answer as JSON in
`choices[0].message.content`. `GET /health` and `GET /v1/models` are also
available. If `PARSER_KEY` is configured as a Worker secret, every endpoint
requires `Authorization: Bearer …`.

From this directory:

```bash
npm install
npm test
npm run gate:dl
npm run check
npm run dev
```

Regenerate the bundled lexicon after changing `data/lexicon.jsonl`:

```bash
python3 scripts/build_parser_lexicon.py
```

Cloudflare deployment uses `npm run deploy` from `grammar/`, then configures
`PARSER_URL_TALEMA` in grammarapp to the Worker's base URL. Set the same
`PARSER_KEY` secret on the Worker and grammarapp when using a private parser.
The Worker does not need a container or a neural model for standard written
Talema. A learned repair model could be added later for malformed input or
speech transcription uncertainty.
