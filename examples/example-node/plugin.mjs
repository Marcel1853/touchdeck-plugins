// Example of an advanced TouchDeck plugin in Node.js (full rights, only in advanced mode).
// TouchDeck talks to the program with JSON lines: messages arrive on stdin, answers go to stdout.
// Everything written to stderr shows up in the TouchDeck log. Only the Node standard library is used.
//
// Shows:
//   - actions with fields and the button that was pressed (info.buttonId)
//   - values: setValue and getValue (with an answer)
//   - triggers: fire, with data for {Event.…} placeholders
//   - TouchDeck events (page_view, value_change …) that arrive without asking
//   - calls with an answer: deck.showPage, deck.setLook, deck.resetLook, deck.timer, status
//   - live displays from "lives": text, bar, "on" look, a real number and several series for graphs
import os from 'node:os';
import readline from 'node:readline';

const send = (msg) => process.stdout.write(`${JSON.stringify(msg)}\n`);
const log = (message, level = 'info') => send({ type: 'log', level, message });

// Questions to TouchDeck (getValue, call) get an answer later with the same requestId.
let nextId = 0;
const waiting = new Map();
function ask(msg) {
  const requestId = `n_${++nextId}`;
  return new Promise((resolve, reject) => {
    waiting.set(requestId, { resolve, reject });
    send({ ...msg, requestId });
    setTimeout(() => {
      if (waiting.delete(requestId)) reject(new Error('TouchDeck did not answer'));
    }, 5000);
  });
}
const getValue = (name) => ask({ type: 'getValue', name });
const call = (op, args = {}) => ask({ type: 'call', op, args });
const setValue = (name, value) => send({ type: 'setValue', name, value: String(value) });
const live = (id, value) => call('live.set', { id, value }).catch((err) => log(err.message, 'warn'));

let settings = {};
let count = 0;
const lit = new Set();

const actions = {
  // Counts presses, writes the count into a value and fires a trigger every N presses.
  async count() {
    count += 1;
    setValue('Node.Presses', count);
    const every = Math.max(1, Number(settings.every) || 5);
    if (count % every === 0) send({ type: 'fire', trigger: 'reached', data: { Count: count } });
    live('presses', { text: `${count}×`, value: ((count % every) / every) * 100, number: count });
    return `Presses: ${count}`;
  },

  // Reads a TouchDeck value (getValue) and returns it as the message of the button.
  async read(params) {
    const value = await getValue(params.value || 'Node.Presses');
    return value ?? '(empty)';
  },

  // Lights the pressed button red; pressing again brings back its own look.
  async light(params, info) {
    const button = info?.buttonId;
    if (!button) throw new Error('Only works on a button');
    if (lit.delete(button)) {
      await call('deck.resetLook', { button });
      return 'off';
    }
    lit.add(button);
    await call('deck.setLook', { button, look: { title: params.title || 'ON', color: '#c0392b', textColor: '#ffffff', icon: '🔴' } });
    return 'on';
  },

  // Shows a page on all devices (ID or name).
  async page(params) {
    await call('deck.showPage', { page: params.page });
    return params.page;
  },

  // Starts, stops or resets a TouchDeck timer.
  async timer(params) {
    await call('deck.timer', { name: params.name || 'Node', op: params.op || 'start', seconds: Number(params.seconds) || 60 });
    return `${params.name || 'Node'}: ${params.op || 'start'}`;
  },

  // Returns data instead of a text: TouchDeck shows it (names and units from "returns" in plugin.json)
  // and passes it on to the following actions as {Result.free}, {Result.uptime}, {Result.load}.
  async system() {
    return { data: { free: os.freemem(), uptime: Math.round(os.uptime()), load: Math.round((os.loadavg()[0] / os.cpus().length) * 100) } };
  },

  // Asks TouchDeck which devices are connected.
  async devices() {
    const status = await call('status');
    const names = (status.devices ?? []).map((d) => d.name).join(', ');
    setValue('Node.Devices', names);
    return `${status.devices?.length ?? 0} device(s)`;
  },
};

// Every few seconds: memory as live display with a real number (MB) and two series for a stacked graph.
function sample() {
  const total = os.totalmem() / 2 ** 20;
  const free = os.freemem() / 2 ** 20;
  const used = total - free;
  live('memory', {
    text: `${(used / 1024).toFixed(1)} GB`,
    value: (used / total) * 100,
    number: Math.round(used),
    on: used / total > 0.9,
    series: { Used: Math.round(used), Free: Math.round(free) },
  });
}

// TouchDeck events arrive on their own; here they are logged and one becomes a trigger.
function onEvent(kind, data) {
  if (kind === 'page_view') {
    setValue('Node.LastPage', data.Page ?? data.Seite ?? '');
    send({ type: 'fire', trigger: 'page', data: { Page: data.Page ?? data.Seite ?? '' } });
  } else if (kind === 'value_change' && !String(data.Name ?? '').startsWith('Node.')) {
    log(`Value ${data.Name} changed`);
  }
}

readline.createInterface({ input: process.stdin }).on('line', async (line) => {
  const msg = JSON.parse(line);
  switch (msg.type) {
    case 'start':
      settings = msg.settings ?? {};
      log(`Node example started (TouchDeck ${msg.touchdeck})`);
      sample();
      setInterval(sample, Math.max(1, Number(settings.interval) || 3) * 1000);
      break;
    case 'action':
      try {
        const out = await actions[msg.id](msg.params ?? {}, msg.info ?? {});
        // { data: {…} } = return as data, anything else = message text.
        if (out?.data) send({ type: 'result', requestId: msg.requestId, ok: true, data: out.data });
        else send({ type: 'result', requestId: msg.requestId, ok: true, message: String(out) });
      } catch (err) {
        send({ type: 'result', requestId: msg.requestId, ok: false, error: err.message });
      }
      break;
    case 'value':
    case 'reply': {
      const w = waiting.get(msg.requestId);
      if (!w) break;
      waiting.delete(msg.requestId);
      if (msg.type === 'value') w.resolve(msg.value);
      else if (msg.ok) w.resolve(msg.result);
      else w.reject(new Error(msg.error));
      break;
    }
    case 'event':
      onEvent(msg.kind, msg.data ?? {});
      break;
    case 'stop':
      process.exit(0);
  }
});
