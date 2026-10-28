'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const bundlePath = process.env.LOLPING_SOURCE;
const source = fs.readFileSync(bundlePath, 'utf8');
const start = source.indexOf('const isRecord = (v) =>');
const end = source.indexOf('const FRONT_POLL_MS =', start);
assert(start >= 0 && end > start, 'Cannot locate provider adapter section');
class ProviderError extends Error {
  constructor(kind, message, status) { super(message); this.kind = kind; this.status = status; }
}
const ctx = vm.createContext({ Buffer, TextDecoder, ProviderError, console });
vm.runInContext(source.slice(start, end) + '\nglobalThis.adapters = { openaiCompatAdapter, anthropicAdapter };', ctx);
const { openaiCompatAdapter, anthropicAdapter } = ctx.adapters;
const openaiProfile = { baseUrl: 'https://unit.test/v1', provider: 'deepseek' };
const anthropicProfile = { baseUrl: 'https://unit.test' };
const request = { model: 'unit-test', system: 'Return final answer', tools: [], turns: [] };
const handlers = { accepted() {}, text() {}, call() {}, usage() {} };
function event(data, name) { return `${name ? `event: ${name}\n` : ''}data: ${typeof data === 'string' ? data : JSON.stringify(data)}\n\n`; }
function fakeFetch(sse) {
  return async () => new Response(sse, { status: 200, headers: { 'content-type': 'text/event-stream' } });
}
function openai(sse) { return openaiCompatAdapter(openaiProfile, '', fakeFetch(sse)).turn(request, handlers, new AbortController().signal); }
function anthropic(sse) { return anthropicAdapter(anthropicProfile, '', fakeFetch(sse)).turn(request, handlers, new AbortController().signal); }
function oaiDelta(delta, finish_reason = null) { return event({ choices: [{ index: 0, delta, finish_reason }] }); }
function antEvent(type, data = {}) { return event({ type, ...data }, type); }
function antStart() { return antEvent('message_start', { message: { role: 'assistant', usage: { input_tokens: 10, output_tokens: 0 } } }); }
function antText(text) {
  return antEvent('content_block_start', { index: 0, content_block: { type: 'text', text: '' } }) +
    antEvent('content_block_delta', { index: 0, delta: { type: 'text_delta', text } }) +
    antEvent('content_block_stop', { index: 0 });
}
function antEnd(stop_reason) { return antEvent('message_delta', { delta: { stop_reason, stop_sequence: null }, usage: { output_tokens: 10 } }) + antEvent('message_stop'); }

test('OpenAI / DeepSeek: normal stop plus DONE succeeds', async () => {
  const result = await openai(oaiDelta({ content: 'B' }) + oaiDelta({}, 'stop') + event('[DONE]'));
  assert.equal(result.text, 'B');
  assert.equal(result.calls.length, 0);
});
test('OpenAI / DeepSeek: completed answer tool call succeeds', async () => {
  const result = await openai(oaiDelta({ tool_calls: [{ index: 0, id: 'call_1', type: 'function', function: { name: 'answer', arguments: '{"markdown":"B"}' } }] }) + oaiDelta({}, 'tool_calls') + event('[DONE]'));
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].name, 'answer');
  assert.equal(JSON.parse(result.calls[0].args).markdown, 'B');
});
test('OpenAI / DeepSeek: EOF before finish reason must reject partial text', async () => {
  await assert.rejects(openai(oaiDelta({ content: 'English: The value increased from' })), 'Partial EOF must not be treated as a successful answer');
});
test('OpenAI / DeepSeek: length finish reason must reject truncated text', async () => {
  await assert.rejects(openai(oaiDelta({ content: 'English: The value increased from' }) + oaiDelta({}, 'length') + event('[DONE]')), 'Token-limited output must not be treated as a successful answer');
});
test('OpenAI / DeepSeek: content_filter finish reason must reject', async () => {
  await assert.rejects(openai(oaiDelta({ content: 'Partial' }) + oaiDelta({}, 'content_filter') + event('[DONE]')), 'Filtered output must not be treated as a successful answer');
});
test('Anthropic: normal end_turn and message_stop succeeds', async () => {
  const result = await anthropic(antStart() + antText('B') + antEnd('end_turn'));
  assert.equal(result.text, 'B');
  assert.equal(result.calls.length, 0);
});
test('Anthropic: completed answer tool_use succeeds', async () => {
  const sse = antStart() +
    antEvent('content_block_start', { index: 0, content_block: { type: 'tool_use', id: 'toolu_1', name: 'answer', input: {} } }) +
    antEvent('content_block_delta', { index: 0, delta: { type: 'input_json_delta', partial_json: '{"markdown":"B"}' } }) +
    antEvent('content_block_stop', { index: 0 }) + antEnd('tool_use');
  const result = await anthropic(sse);
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].name, 'answer');
  assert.equal(JSON.parse(result.calls[0].args).markdown, 'B');
});
test('Anthropic: EOF without message_stop must reject partial text', async () => {
  await assert.rejects(anthropic(antStart() + antText('English: The value increased from')), 'Partial EOF must not be treated as a successful answer');
});
test('Anthropic: max_tokens finish must reject truncated text', async () => {
  await assert.rejects(anthropic(antStart() + antText('English: The value increased from') + antEnd('max_tokens')), 'Token-limited output must not be treated as a successful answer');
});
test('OpenAI / DeepSeek: DONE without a terminal finish reason must reject', async () => {
  await assert.rejects(openai(oaiDelta({ content: 'Partial' }) + event('[DONE]')), 'DONE alone does not establish that the model completed its answer');
});
test('Anthropic: message_stop without a valid stop_reason must reject', async () => {
  await assert.rejects(anthropic(antStart() + antText('Partial') + antEvent('message_stop')), 'message_stop alone does not establish a normal model completion');
});
