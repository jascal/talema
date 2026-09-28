import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { parseTalema } from '../parser.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const rows = fs.readFileSync(path.join(root, '../data/sentences.jsonl'), 'utf8')
  .trim().split('\n').map(JSON.parse).filter(row => row.kind !== 'dialect');
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'talema-dl-'));
try {
  const facts = [];
  const expected = new Set();
  const forms = [];
  const expectedRelations = new Set();
  rows.forEach((row, index) => {
    const tokens = parseTalema(row.talema).sentences[0].tokens;
    for (const token of tokens) {
      facts.push(`${index + 1}\t${token.id}\t${token.arity}`);
      forms.push(`${index + 1}\t${token.id}\t${token.root}\t${token.cls || '-'}\t${token.literal ? 1 : 0}`);
      if (token.head) expected.add(`${index + 1}\t${token.id}\t${token.head}`);
      expectedRelations.add(`${index + 1}\t${token.id}\t${token.relation}`);
    }
  });
  const early = rows.length + 1;
  const incomplete = rows.length + 2;
  facts.push(`${early}\t1\t0`, `${early}\t2\t0`, `${incomplete}\t1\t2`, `${incomplete}\t2\t0`);
  fs.writeFileSync(path.join(work, 'word.facts'), facts.join('\n') + '\n');
  fs.writeFileSync(path.join(work, 'form.facts'), forms.join('\n') + '\n');
  execFileSync('souffle', ['-F', work, '-D', work, path.join(root, 'parse.dl')], { stdio: 'inherit' });
  const got = new Set(fs.readFileSync(path.join(work, 'parent.csv'), 'utf8').trim().split('\n'));
  const invalid = new Set(fs.readFileSync(path.join(work, 'invalid.csv'), 'utf8').trim().split('\n'));
  const relations = new Set(fs.readFileSync(path.join(work, 'relation.csv'), 'utf8').trim().split('\n'));
  if (got.size !== expected.size || [...expected].some(link => !got.has(link))
      || relations.size !== expectedRelations.size
      || [...expectedRelations].some(relation => !relations.has(relation))
      || !invalid.has(`${early}\tearly_complete`) || !invalid.has(`${incomplete}\tincomplete`)) {
    throw new Error(`Datalog parity failed: ${got.size} links, ${relations.size} labels, invalid=${[...invalid]}`);
  }
  console.log(`Datalog parity: ${rows.length} sentences, ${got.size} parent links, ${relations.size} labels, malformed trees rejected`);
} finally {
  fs.rmSync(work, { recursive: true, force: true });
}
