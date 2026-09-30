// Reads JSON lines {i, text} on stdin; writes one JSON line per input with the exact parser's verdict.
// {i, ok, unknown: [roots], unknown_nodes: [{root, start, end}], nodes, error: null}
//   or {i, ok: false, error: {code, message, start, end}}   (start/end are character offsets or null)
import { parseTalema } from '../../grammar/parser.mjs';
import { createInterface } from 'node:readline';

function walk(node, out) {
  out.nodes += 1;
  if (node.known === false && !node.literal) {
    out.unknown.push(node.root);
    out.unknown_nodes.push({ root: node.root, start: node.start, end: node.end });
  }
  for (const child of node.children) walk(child, out);
}

const rl = createInterface({ input: process.stdin });
for await (const line of rl) {
  if (!line.trim()) continue;
  const { i, text } = JSON.parse(line);
  try {
    const parsed = parseTalema(text);
    const out = { nodes: 0, unknown: [], unknown_nodes: [] };
    for (const s of parsed.sentences) walk(s.tree, out);
    process.stdout.write(JSON.stringify({ i, ok: true, sentences: parsed.sentences.length, ...out, error: null }) + '\n');
  } catch (e) {
    process.stdout.write(JSON.stringify({ i, ok: false, error: { code: e.code || 'ERROR', message: String(e.message),
      start: e.start ?? null, end: e.end ?? null } }) + '\n');
  }
}
