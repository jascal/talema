import { parseTalema, TalemaParseError } from './parser.mjs';

const MAX_BODY_BYTES = 4096;
const encoder = new TextEncoder();

function json(value, status = 200) {
  return Response.json(value, { status, headers: { 'cache-control': 'no-store' } });
}

function authorized(request, env) {
  if (!env.PARSER_KEY) return true;
  const got = request.headers.get('authorization')?.replace(/^Bearer /iu, '') || '';
  const a = encoder.encode(got);
  const b = encoder.encode(env.PARSER_KEY);
  if (a.byteLength !== b.byteLength) return !crypto.subtle.timingSafeEqual(a, a);
  return crypto.subtle.timingSafeEqual(a, b);
}

async function smallJson(request) {
  const reader = request.body?.getReader();
  if (!reader) throw new TalemaParseError('BAD_REQUEST', 'JSON request body required.');
  const pieces = [];
  let length = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > MAX_BODY_BYTES) {
      await reader.cancel();
      throw new TalemaParseError('REQUEST_TOO_LARGE', 'Request body is too large.');
    }
    pieces.push(value);
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const piece of pieces) { bytes.set(piece, offset); offset += piece.byteLength; }
  try { return JSON.parse(new TextDecoder().decode(bytes)); }
  catch { throw new TalemaParseError('BAD_JSON', 'Request body must be JSON.'); }
}

function errorBody(error) {
  return { kind: 'abstain', reason: error.code || 'PARSER_ERROR', message: error.message,
    start: error.start ?? null, end: error.end ?? null };
}

function completion(answer) {
  return { id: crypto.randomUUID(), object: 'chat.completion', model: 'talema-three-rules-v1',
    choices: [{ index: 0, finish_reason: 'stop', message: { role: 'assistant', content: JSON.stringify(answer) } }] };
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (!authorized(request, env)) return json({ error: 'unauthorized' }, 401);
    if (request.method === 'GET' && path === '/health') {
      return json({ ok: true, engine: 'talema-exact', lang: 'talema', transform: 'three-rules',
        model: 'talema-three-rules-v1' });
    }
    if (request.method === 'GET' && path === '/v1/models') {
      return json({ object: 'list', data: [{ id: 'talema-three-rules-v1', object: 'model' }] });
    }
    if (request.method !== 'POST' || !['/parse', '/v1/chat/completions'].includes(path)) {
      return json({ error: 'not found' }, 404);
    }
    const openai = path === '/v1/chat/completions';
    try {
      const body = await smallJson(request);
      if (body.lang && body.lang !== 'talema') {
        throw new TalemaParseError('WRONG_LANGUAGE', 'This expert parses Talema only.');
      }
      const text = openai ? body.messages?.filter(m => m.role === 'user').at(-1)?.content : body.text;
      const answer = parseTalema(text);
      return json(openai ? completion(answer) : answer);
    } catch (error) {
      const answer = errorBody(error);
      return json(openai ? completion(answer) : answer,
        openai ? 200 : (error.code === 'REQUEST_TOO_LARGE' ? 413 : 422));
    }
  }
};
