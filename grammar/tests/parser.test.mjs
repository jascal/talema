import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parseTalema, TalemaParseError } from '../parser.mjs';
import worker from '../worker.mjs';
import lexicon from '../lexicon.mjs';

const rows = fs.readFileSync(fileURLToPath(new URL('../../data/sentences.jsonl', import.meta.url)), 'utf8')
  .trim().split('\n').map(JSON.parse);

test('bundled lexicon matches the dataset source', () => {
  const source = fs.readFileSync(fileURLToPath(new URL('../../data/lexicon.jsonl', import.meta.url)), 'utf8')
    .trim().split('\n').map(JSON.parse);
  assert.equal(Object.keys(lexicon).length, source.length);
  for (const row of source) {
    assert.deepEqual(lexicon[row.root], [row.cls, row.en, row.de, row.es], row.root);
  }
});

function sourceParents(source) {
  const parts = source.match(/\(|\)|"[^"]*"|[^\s()]+/gu) || [];
  let at = 0, nextId = 0;
  const parents = [];
  function read(parent = 0) {
    const group = parts[at] === '(';
    if (group) at++;
    assert.ok(parts[at] && parts[at] !== ')', `bad source tree: ${source}`);
    at++; // concept or literal name
    const id = ++nextId;
    parents.push(parent);
    if (group) {
      while (parts[at] !== ')') read(id);
      at++;
    }
  }
  read();
  assert.equal(at, parts.length, `trailing source tree: ${source}`);
  return parents;
}

test('all standard exported sentences reconstruct their authored tree shape', () => {
  let count = 0;
  for (const row of rows) {
    if (row.kind === 'dialect') continue;
    const result = parseTalema(row.talema);
    assert.equal(result.sentences.length, 1, row.id);
    assert.deepEqual(result.sentences[0].tokens.map(t => t.head), sourceParents(row.tree), row.id);
    count++;
  }
  assert.equal(count, 1560);
});

test('arity, offsets, relators, loans, and multiple sentences', () => {
  const text = 'bi fura pe si tova tova . Ana-a .';
  const parsed = parseTalema(text);
  assert.equal(parsed.sentences.length, 2);
  assert.deepEqual(parsed.sentences[0].tokens.map(t => t.head), [0, 1, 1, 3, 4, 4]);
  assert.equal(parsed.sentences[0].tokens[2].relation, 'subject relator');
  assert.equal(text.slice(parsed.sentences[1].tokens[0].start, parsed.sentences[1].tokens[0].end), 'Ana-a');
  assert.equal(parsed.sentences[1].tokens[0].literal, true);
});

test('malformed text reports a precise failure and new roots remain parseable', () => {
  for (const [text, code] of [
    ['bi fura .', 'INCOMPLETE_TREE'],
    ['ba ma .', 'EXTRA_WORD'],
    ['bi fura pe si tova tova', 'MISSING_PERIOD'],
    ['xo .', 'BAD_WORD'],
    ['p-e .', 'INCOMPLETE_TREE'],
  ]) {
    assert.throws(() => parseTalema(text), error => error instanceof TalemaParseError && error.code === code);
  }
  const newRoot = parseTalema('fvfa .');
  assert.deepEqual(newRoot.warnings, [{ code: 'UNKNOWN_ROOT', sentence: 1, root: 'fvf' }]);
});

test('Worker exposes direct and parser-spoke contracts', async () => {
  const direct = await worker.fetch(new Request('https://talema.invalid/parse', { method: 'POST',
    body: JSON.stringify({ text: 'talema .' }) }), {});
  assert.equal(direct.status, 200);
  assert.equal((await direct.json()).sentences[0].tree.word, 'talema');

  const spoke = await worker.fetch(new Request('https://talema.invalid/v1/chat/completions', {
    method: 'POST', body: JSON.stringify({ lang: 'talema', messages: [{ role: 'user', content: 'talema .' }] })
  }), {});
  assert.equal(spoke.status, 200);
  assert.equal(JSON.parse((await spoke.json()).choices[0].message.content).kind, 'parse');
  const bad = await worker.fetch(new Request('https://talema.invalid/parse', { method: 'POST',
    body: JSON.stringify({ text: 'ba ma .' }) }), {});
  assert.equal(bad.status, 422);
  assert.equal((await bad.json()).reason, 'EXTRA_WORD');
});
