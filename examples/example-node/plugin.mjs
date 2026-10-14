// Example of an advanced TouchDeck plugin in Node.js (full rights, only in advanced mode).
// TouchDeck talks to the program with JSON lines: messages arrive on stdin, answers go to stdout.
import readline from 'node:readline';

const send = (msg) => process.stdout.write(`${JSON.stringify(msg)}\n`);
const log = (message, level = 'info') => send({ type: 'log', level, message });

let count = 0;

const actions = {
  press() {
    count += 1;
    send({ type: 'setValue', name: 'Node.Presses', value: String(count) });
    if (count % 5 === 0) send({ type: 'fire', trigger: 'five', data: { Count: count } });
    return `Presses: ${count}`;
  },
};

readline.createInterface({ input: process.stdin }).on('line', (line) => {
  const msg = JSON.parse(line);
  if (msg.type === 'start') log(`Node example started (TouchDeck ${msg.touchdeck})`);
  else if (msg.type === 'action') {
    try {
      send({ type: 'result', requestId: msg.requestId, ok: true, message: actions[msg.id](msg.params ?? {}) });
    } catch (err) {
      send({ type: 'result', requestId: msg.requestId, ok: false, error: err.message });
    }
  } else if (msg.type === 'stop') process.exit(0);
});
