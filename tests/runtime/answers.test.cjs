const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const crypto = require('node:crypto');
const events = require('node:events');
const assert = require('node:assert/strict');
const { test, afterEach } = require('node:test');
const source = fs.readFileSync(process.env.LOLPING_SOURCE, 'utf8');
const common = require(process.env.LOLPING_TOOLS);
function section(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert(a >= 0 && b > a, `Cannot locate ${start}`);
  return source.slice(a, b);
}
const context = vm.createContext({
  node_events: events, node_crypto: crypto, path, promises: fs.promises,
  _commonjsHelpers: common, Buffer, AbortController, setTimeout, clearTimeout, console,
  isSessionId: () => false,
  isBuiltin: p => p.kind === 'builtin',
  strings: () => ({ teammate: { intent: {generic:{label:'提问',instruction:''}}, ask: { failed: { timeout: '请求超时', other: '回答失败' } } } }),
  LANGUAGE_NAMES: { en: 'English', 'zh-CN': 'Chinese' },
});
vm.runInContext([
  section('class RateLimiter {', 'const DEFAULT_FLOOD_LIMITS'),
  section('const def = (id, kind, extra', 'function isValidWheel('),
  section('function threadAction(', 'function wordsContinuesByDefault('),
  section('let counter = 0;', 'const RECEIPT_OFFSET'),
  section('const RECEIPT_OFFSET', 'const MAX_SPOTS'),
  section('const LIMIT = { en:', 'const KINDS ='),
  section('function resolveTarget(at2, ctx)', 'const same ='),
  section('const VOCABULARY =', 'const spotNumber ='),
  section('const spotNumber =', 'const MAX_ROUNDS ='),
  section('function fileSection(', 'function contextSections('),
  section('function clip(text2, max2)', 'function located('),
  section('const ALL_READ =', 'const FIELDS_LISTED ='),
  'const FILE_READ_LIMIT = 600000;',
  section('const MAX_ROUNDS =', 'class AskGesture {'),
  'globalThis.Subject = { AskController, AskMachine, toolsFor, fileSection };',
].join('\n'), context);
const { AskController, AskMachine, toolsFor, fileSection } = context.Subject;
const fixtures = [];
afterEach(() => { for (const f of fixtures.splice(0)) dispose(f); });

function fixture(intent = 'allin') {
  const shown = [], copied = [], saved = [];
  const settings = { teammate: { receiptSound: false, intents: {}, context: {} } };
  const overlay = { toLocal: p => p, toDip: p => p, primaryDip: () => ({x:0,y:0}) };
  for (const name of ['spawnMate', 'spawnMateEmote', 'mateSaid', 'fadeMate', 'clearMate']) {
    overlay[name] = (...args) => shown.push({ name, args });
  }
  const windows = { placeOf: () => null };
  for (const name of ['showBubble', 'updateBubble', 'showCard', 'updateCard', 'hideBubble', 'hideCard']) {
    windows[name] = (...args) => shown.push({ name, args });
  }
  const controller = new AskController({
    now: () => 1234, overlay, windows, settings: () => settings,
    thumbnail: () => '', secrets: { instructions: () => '' },
    agents: { bridge: { command: () => ({}) } },
    history: { append: async (...args) => { saved.push(args); return null; } },
    copyAnswer: text => copied.push(text), cursor: () => ({x:600,y:420}),
  });
  const machine = new AskMachine(() => 1234);
  machine.sent();
  const run = {
    machine, abort: new AbortController(), deadlines: [], ended: false, visitor: null,
    spots: [{ intent, phys: { x: 50, y: 50 }, displayId: 1 }],
    spot: { intent, phys: { x: 50, y: 50 }, displayId: 1 },
    receipt: { x: 50, y: 50 }, intent: { custom: '', def: { id: intent, kind: 'answer' }, label: intent === 'allin' ? 'FRQ' : 'MCQ' },
    autoCard: true, lang: 'zh-CN', tag: { name: '_' }, emotes: true,
    profile: null, app: 'Test', title: 'Test question', thread: null, thumb: '',
    text: '', line: '', said: '', rest: '', markdown: [], marks: [], pings: 0,
    calls: [], early: [], stale: false, bubbleBack: false, fileRead: 0,
    used: [], skipped: false, screenMarks: [],
    shot: { area: {x:0,y:0,w:100,h:100}, overview: {w:100,h:100} },
    display: { rect: {x:0,y:0,w:100,h:100} },
  };
  controller.run = controller.shown = run;
  const f = { controller, run, shown, copied, saved };
  fixtures.push(f);
  return f;
}
function dispose(f) { f.controller.cancel('user'); }

function assertFinalDialog(f, answer, x = 624, y = 444) {
  const cards = f.shown.filter(item => item.name === 'showCard');
  assert.equal(cards.length, 1, 'One final answer dialog must open');
  assert.equal(cards[0].args[0].x, x);
  assert.equal(cards[0].args[0].y, y);
  const state = cards[0].args[1];
  assert.equal(state.streaming, false);
  assert.equal(state.answerOnly, true);
  assert.equal(state.entries.length, 1);
  assert.equal(state.entries[0].markdown, answer);
  assert.equal(state.entries[0].line, '');
  assert.equal(cards[0].args[2].focus, false);
  assert.equal(f.shown.some(item => ['showBubble','spawnMate','spawnMateEmote'].includes(item.name)), false);
}

test('receipt advances request state without showing any mark or sound', () => {
  const f = fixture();
  f.controller.received(f.run);
  assert.equal(f.run.machine.phase, 'received');
  assert.deepEqual(f.shown, []);
  dispose(f);
});
test('step pings and emotes have no visual side effect', () => {
  const f = fixture();
  f.controller.placePing(f.run, { type: 'allin', at: { spot: 1 } });
  f.controller.placeEmote(f.run, { slug: 'gg_heart', at: { spot: 1 } });
  assert.deepEqual(f.shown, []);
  assert.equal(f.run.marks.length, 0);
  dispose(f);
});
test('streaming an answer never opens a card or bubble', () => {
  const f = fixture();
  f.controller.say(f.run, '短摘要');
  f.controller.addAnswer(f.run, 'English: A complete answer.\n中文：完整答案。');
  assert.deepEqual(f.shown, []);
  dispose(f);
});
test('completed FRQ copies full bilingual answer instead of short summary and saves history', async () => {
  const f = fixture();
  const answer = 'English: The value increased from 20 to 30, so it increased by 50%.\n中文：数值从20增加到30，因此增加了50%。';
  f.controller.say(f.run, '这是摘要');
  f.controller.addAnswer(f.run, answer);
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, [answer]);
  assertFinalDialog(f, answer);
  assert.equal(f.saved.length, 1);
  assert.equal(f.saved[0][1].markdown, answer);
  dispose(f);
});
test('plain-text fallback preserves long answer without bubble truncation', async () => {
  const f = fixture();
  const answer = 'English: ' + 'The data show a clear increase. '.repeat(30) + '\n中文：数据表现出明显增长。';
  f.run.text = answer;
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, [answer]);
  assertFinalDialog(f, answer);
  dispose(f);
});
test('MCQ completion places only the returned option letter on clipboard', async () => {
  const f = fixture('danger');
  f.controller.addAnswer(f.run, 'B');
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, ['B']);
  assertFinalDialog(f, 'B');
  dispose(f);
});
test('MCQ normalizes an unambiguous answer prefix to just a letter', async () => {
  const f = fixture('danger');
  f.controller.addAnswer(f.run, 'The answer is B.');
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, ['B']);
});
test('MCQ explanation or malformed output cannot become a clipboard answer', async () => {
  const f = fixture('danger');
  f.controller.addAnswer(f.run, 'Maybe B, because it looks larger.');
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, []);
  assert.deepEqual(f.shown, []);
});
test('MCQ retains question numbers and selected letters for multiple questions', async () => {
  const f = fixture('danger');
  f.controller.addAnswer(f.run, '1. B\n2. A, C');
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, ['1. B\n2. A,C']);
});
test('a revised final answer replaces an earlier answer instead of copying both', async () => {
  const f = fixture('danger');
  f.controller.addAnswer(f.run, 'A');
  f.controller.addAnswer(f.run, 'B');
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, ['B']);
});
test('code-only answer does not trigger the no-summary overlay fallback', async () => {
  const f = fixture();
  const answer = '```text\nFinal result\n```';
  f.controller.addAnswer(f.run, answer);
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, [answer]);
  assertFinalDialog(f, answer);
});
test('failed request remains silent and leaves clipboard untouched', () => {
  const f = fixture();
  f.controller.fail(f.run, 'timeout');
  assert.equal(f.run.machine.failure, 'timeout');
  assert.deepEqual(f.shown, []);
  assert.deepEqual(f.copied, []);
  dispose(f);
});
test('cancelled or superseded request cannot overwrite newer clipboard answer', async () => {
  const f = fixture();
  f.run.markdown.push('stale answer');
  f.controller.stopRun();
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, []);
  dispose(f);
});
test('duplicate finish cannot copy or save the same answer twice', async () => {
  const f = fixture();
  f.run.markdown.push('B');
  await f.controller.finish(f.run);
  await f.controller.finish(f.run);
  assert.deepEqual(f.copied, ['B']);
  assert.equal(f.saved.length, 1);
  dispose(f);
});
test('provider is offered answer and reading tools without screen or action tools', () => {
  const f = fixture();
  const defs = toolsFor(f.run, { file: {}, fields: [], system: null });
  assert.deepEqual(Array.from(defs, d => d.name).sort(), ['answer', 'look', 'read_file']);
  dispose(f);
});
test('MCQ can request a sharper image before selecting an option', () => {
  const f = fixture('danger');
  const defs = toolsFor(f.run, { file: {}, fields: [], system: null });
  assert.deepEqual(Array.from(defs, d => d.name).sort(), ['answer', 'look', 'read_file']);
});
test('whole document context includes earlier and later pages outside visible range', () => {
  const doc = { name: 'article.pdf', kind: 'pdf', outline: ['p. 1', 'p. 2', 'p. 3'], sections: [
    {label:'p. 1', text:'EARLIER: baseline 20'},
    {label:'p. 2', text:'VISIBLE: chart compares years'},
    {label:'p. 3', text:'LATER: final value 30'},
  ] };
  const text = fileSection({ doc, from: 1, to: 1 });
  assert.match(text, /EARLIER: baseline 20/);
  assert.match(text, /LATER: final value 30/);
});
test('oversized document context explicitly reports incomplete coverage', () => {
  const doc = { name:'long.pdf', kind:'pdf', outline: ['p. 1', 'p. 2'], sections:[
    {label:'p. 1', text:'x'.repeat(600001)}, {label:'p. 2', text:'last page'},
  ] };
  const text = fileSection({doc,from:0,to:0});
  assert.ok(/incomplete|truncated/i.test(text), 'Document coverage must be marked incomplete');
  assert.ok(text.length < 601000);
});
test('scene uses original complete document instead of a visible-section preview clipped at 90k', () => {
  const f = fixture();
  const full = { name:'article.txt',kind:'text',outline:['part 1'],sections:[{label:'part 1',text:'x'.repeat(90001)+'IMPORTANT END'}] };
  const preview = { ...full, sections:[{label:'part 1',text:full.sections[0].text.slice(0,90000)}] };
  const ctx = f.controller.useScene(f.run, {
    layers:{marks:[],system:null,fields:[],boxes:[],doc:full,used:[],skipped:false,file:{doc:preview,from:0,to:0}},
    shot:f.run.shot,overviewJpeg:Buffer.from(''),zoomJpegs:[],
  });
  assert.ok(fileSection(ctx.file).includes('IMPORTANT END'), 'End of the original document must reach the model');
});
test('agent timeout after partial output fails without copying the partial answer', async () => {
  const f = fixture();
  const due = [];
  f.controller.deadline = (_run, _ms, fn) => due.push(fn);
  void f.controller.askAgent(f.run,{id:'test',kind:'agent',preset:'custom',name:'Test',timeoutS:1},'',{scene:()=>new Promise(()=>{})});
  f.controller.addAnswer(f.run,'unfinished partial answer');
  due[0]();
  await Promise.resolve();
  assert.equal(f.run.machine.failure, 'timeout');
  assert.deepEqual(f.copied, []);
});
function providerFixture(responses, intent='danger') {
  const f = fixture(intent);
  const doc = {name:'article.txt',kind:'text',outline:['part 1'],sections:[{label:'part 1',text:'Complete article'}]};
  f.run.reading = {
    front:Promise.resolve({app:'Test',title:'Question',window:'1',profile:{id:'test',kind:'builtin',model:'test-model'},key:'',route:''}),
    scene:async()=>({layers:{marks:[],system:null,fields:[],boxes:[],doc,used:[],skipped:false,file:{doc,from:0,to:0}},shot:f.run.shot,overviewJpeg:Buffer.from(''),zoomJpegs:[]}),
  };
  f.controller.deps.adapter = ()=>({turn:async()=>responses.shift()});
  f.controller.look = async()=>[{text:'A closer view of the chart'}];
  return f;
}
test('multi-round plain text copies only final response after reading', async () => {
  const f=providerFixture([
    {text:'I will read the chart.',calls:[{id:'read1',name:'look',args:'{"x":0,"y":0,"w":10,"h":10}'}]},
    {text:'B',calls:[]},
  ]);
  await f.controller.answer(f.run);
  assert.deepEqual(f.copied,['B']);
});
test('exhausting read rounds cannot copy a preliminary answer', async () => {
  const responses=Array.from({length:6},(_,i)=>({text:'',calls:[
    {id:`answer${i}`,name:'answer',args:'{"markdown":"Preliminary answer"}'},
    {id:`read${i}`,name:'read_file',args:'{"pages":"1"}'},
  ]}));
  const f=providerFixture(responses,'allin');
  await f.controller.answer(f.run);
  assert.deepEqual(f.copied,[]);
  assert.equal(f.run.machine.failure,'other');
});

test('final dialog follows cursor location at completion, not the question spot', async () => {
  const f=fixture('danger');
  f.controller.deps.cursor=()=>({x:820,y:560});
  f.controller.addAnswer(f.run,'B');
  assert.deepEqual(f.shown,[]);
  await f.controller.finish(f.run);
  assertFinalDialog(f,'B',844,584);
});
test('final dialog remains available even when automatic clipboard copy fails', async () => {
  const f=fixture('danger');
  f.controller.deps.copyAnswer=()=>{throw new Error('Clipboard unavailable');};
  f.controller.addAnswer(f.run,'B');
  await f.controller.finish(f.run);
  assertFinalDialog(f,'B');
});
test('continuing a thread hides the previous final dialog until the new answer succeeds', () => {
  const f=fixture();
  f.controller.cardShown=true;
  f.controller.thread={id:'existing',entries:[],lastActivity:1234};
  f.controller.deps.lang=()=>'zh-CN';
  f.controller.deps.tempDir=()=>'/tmp/lolping-test';
  f.controller.deps.overlay.setMateTicket=()=>{};
  f.controller.deps.overlay.displayAt=()=>null;
  f.controller.go=async()=>{};
  f.controller.ask([{intent:'generic',phys:{x:50,y:50},displayId:1}],{text:'follow-up',newThread:false});
  assert.equal(f.controller.cardShown,false);
  assert.deepEqual(f.shown.map(item=>item.name),['hideCard']);
});
