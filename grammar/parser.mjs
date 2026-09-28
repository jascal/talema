import lexicon from './lexicon.mjs';

const VOWELS = 'aeiou';
const CONSONANTS = 'ptkbdgmnlrsfvh';
const MAX_CHARS = 2000;
const MAX_WORDS = 512;

export class TalemaParseError extends Error {
  constructor(code, message, start = null, end = null) {
    super(message);
    this.name = 'TalemaParseError';
    this.code = code;
    this.start = start;
    this.end = end;
  }
}

function endingValue(ending) {
  let value = 0;
  for (const vowel of ending) value = value * 5 + VOWELS.indexOf(vowel);
  return value;
}

function tokenize(text) {
  const out = [];
  for (const match of text.matchAll(/\S+/gu)) {
    const chunk = match[0];
    const start = match.index;
    if (chunk === '.') {
      out.push({ word: '.', start, end: start + 1 });
    } else if (chunk.endsWith('.')) {
      const word = chunk.slice(0, -1);
      if (word) out.push({ word, start, end: start + word.length });
      out.push({ word: '.', start: start + word.length, end: start + chunk.length });
    } else {
      out.push({ word: chunk, start, end: start + chunk.length });
    }
  }
  return out;
}

function readWord(token) {
  const word = token.word;
  let root, ending, literal = false;
  if (word.includes('-')) {
    const split = word.lastIndexOf('-');
    root = word.slice(0, split);
    ending = word.slice(split + 1);
    literal = true;
    if (!root || /\s/u.test(root)) {
      throw new TalemaParseError('BAD_LITERAL', `Invalid loan or name: ${word}`, token.start, token.end);
    }
  } else {
    const match = word.match(/^([a-z]*[ptkbdgmnlrsfvh])([aeiou]+)$/u);
    if (!match || ![...match[1]].every(ch => CONSONANTS.includes(ch) || VOWELS.includes(ch))) {
      throw new TalemaParseError('BAD_WORD', `Talema word needs a consonant-final root and a vowel ending: ${word}`, token.start, token.end);
    }
    [, root, ending] = match;
  }
  if (!/^[aeiou]+$/u.test(ending) || (ending.length > 1 && ending[0] === 'a')) {
    throw new TalemaParseError('BAD_ENDING', `Invalid base-five ending: ${word}`, token.start, token.end);
  }
  const arity = endingValue(ending);
  if (arity > MAX_WORDS) {
    throw new TalemaParseError('ARITY_TOO_LARGE', `Ending names too many children: ${word}`, token.start, token.end);
  }
  const entry = literal ? null : lexicon[root];
  return { ...token, root, ending, arity, literal, cls: entry?.[0] || null,
    gloss: entry?.[1]?.split('|')[0] || null,
    de: entry?.[2]?.split('|')[0] || null,
    es: entry?.[3]?.split('|')[0] || null,
    known: Boolean(entry) };
}

function relationFor(word) {
  if (!word.literal && word.arity === 1 && word.root === 'p') return 'subject relator';
  if (!word.literal && word.arity === 1 && word.root === 't') return 'object relator';
  if (!word.literal && word.arity === 1 && word.root === 'pap') return 'recipient relator';
  if (word.cls === 'ADP' || word.cls === 'SCONJ') return 'relator';
  return 'dependent';
}

function parseSentence(words, sentenceIndex) {
  if (!words.length) throw new TalemaParseError('EMPTY_SENTENCE', 'A sentence needs a head word.');
  let next = 0;
  const flat = [];
  const unknownRoots = new Set();
  function read(parent = null) {
    if (next >= words.length) {
      const last = words.at(-1);
      throw new TalemaParseError('INCOMPLETE_TREE', 'The last word ends before all dependents have appeared.', last.end, last.end);
    }
    const word = words[next++];
    const id = flat.length + 1;
    const node = { id, word: word.word, root: word.root, ending: word.ending,
      arity: word.arity, literal: word.literal, known: word.known, cls: word.cls,
      gloss: word.gloss, de: word.de, es: word.es, relation: parent ? relationFor(word) : 'root',
      head: parent?.id || 0, start: word.start, end: word.end, children: [] };
    flat.push(node);
    if (!word.literal && !word.known) unknownRoots.add(word.root);
    for (let i = 0; i < word.arity; i++) node.children.push(read(node));
    return node;
  }
  const tree = read();
  if (next !== words.length) {
    const extra = words[next];
    throw new TalemaParseError('EXTRA_WORD', `Tree is complete before ${extra.word}.`, extra.start, extra.end);
  }
  return { index: sentenceIndex, tree, tokens: flat.map(({ children, ...token }) => token),
    unknownRoots: [...unknownRoots] };
}

/** Decode written Talema by its three rules; no statistical model chooses the tree. */
export function parseTalema(text) {
  if (typeof text !== 'string' || !text.trim()) throw new TalemaParseError('EMPTY_TEXT', 'Enter a Talema sentence.');
  if (text.length > MAX_CHARS) throw new TalemaParseError('TEXT_TOO_LONG', `Limit is ${MAX_CHARS} characters.`);
  const tokens = tokenize(text);
  const sentences = [];
  let words = [];
  let wordCount = 0;
  for (const token of tokens) {
    if (token.word === '.') {
      sentences.push(parseSentence(words, sentences.length + 1));
      words = [];
      continue;
    }
    if (++wordCount > MAX_WORDS) throw new TalemaParseError('TOO_MANY_WORDS', `Limit is ${MAX_WORDS} words.`);
    words.push(readWord(token));
  }
  if (words.length || !sentences.length) {
    const last = tokens.at(-1);
    throw new TalemaParseError('MISSING_PERIOD', 'End each sentence with a period.', last?.end, last?.end);
  }
  return { kind: 'parse', language: 'talema', model: 'talema-three-rules-v1',
    sentences, warnings: sentences.flatMap(sentence => sentence.unknownRoots.map(root =>
      ({ code: 'UNKNOWN_ROOT', sentence: sentence.index, root }))) };
}
