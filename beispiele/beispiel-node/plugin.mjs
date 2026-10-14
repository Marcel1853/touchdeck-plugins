// Beispiel für ein erweitertes TouchDeck-Plugin in Node.js (volle Rechte, nur im erweiterten Modus).
// TouchDeck spricht mit dem Programm über JSON-Zeilen: Nachrichten kommen auf stdin, Antworten gehen auf stdout.
import readline from 'node:readline';

const send = (msg) => process.stdout.write(`${JSON.stringify(msg)}\n`);
const log = (message, level = 'info') => send({ type: 'log', level, message });

let count = 0;

const actions = {
  drueck() {
    count += 1;
    send({ type: 'setValue', name: 'Node.Drücke', value: String(count) });
    if (count % 5 === 0) send({ type: 'fire', trigger: 'fuenf', data: { Anzahl: count } });
    return `Drücke: ${count}`;
  },
};

readline.createInterface({ input: process.stdin }).on('line', (line) => {
  const msg = JSON.parse(line);
  if (msg.type === 'start') log(`Node-Beispiel gestartet (TouchDeck ${msg.touchdeck})`);
  else if (msg.type === 'action') {
    try {
      send({ type: 'result', requestId: msg.requestId, ok: true, message: actions[msg.id](msg.params ?? {}) });
    } catch (err) {
      send({ type: 'result', requestId: msg.requestId, ok: false, error: err.message });
    }
  } else if (msg.type === 'stop') process.exit(0);
});
