# Factorio for TouchDeck

**English** · [Deutsch](README.de.md)

**Advanced TouchDeck plugin** for Factorio 2.1 (with or without Space Age). Shows research, speed,
evolution, power, production, planet and – with UTLogistics – your trains live on your buttons, much
of it as graphs too. Buttons pause, change the speed, save, take screenshots and queue research.

It needs the Factorio mod **[TouchDeck Bridge](https://mods.factorio.com/mod/touchdeck-bridge)** from
the mod portal.

- **Works together with [UTLogistics](https://mods.factorio.com/mod/UTLogistics)** if it is installed in
  Factorio (optional, see below).
- **Linux: tested. Windows: not tested yet** – feedback is welcome.
- Languages: English and German; French, Spanish, Polish, Brazilian Portuguese, Russian and Chinese
  are AI translations (corrections welcome). The ready-made pages are labelled in German.
- The features are **examples** of what a game and TouchDeck can do together. MIT license: feel free
  to build your own plugin or mod from it. **Suggestions are welcome.**

## Setup

1. **Install TouchDeck** (free):
   [github.com/Marcel1853/touchdeck/releases](https://github.com/Marcel1853/touchdeck/releases),
   plus the Android app for your phone or tablet.
2. **Install the plugin:** in TouchDeck switch on advanced mode (*Plugins › Advanced*), then
   *Plugins › Marketplace › **Factorio** › Install*. TouchDeck asks twice because it is an advanced
   plugin.
3. **Install the mod:** in Factorio's main menu under *Mods*, search for **“TouchDeck Bridge”** and
   install it. Or click **“🧩 Install mod”** in the plugin card – the plugin brings the mod along and
   TouchDeck puts it into your Factorio mod folder. Then (re)start Factorio; the mod is switched on
   automatically.
4. **Import the pages:** in the plugin card under “Ready-made pages”, click **Factorio** (with
   UTLogistics also **UTLogistics**). Importing only adds pages – if you have pages of an older
   version, delete them first.
5. **Load a game** – done. The top left button of the page “Factorio” then says “running”.

Requirements: TouchDeck 0.12 or newer, Python 3.8 or newer (usually already there on Linux), an X11
session on Linux. Nothing to set up in Factorio: no launch option, no network, no RCON.

## How it works

- The mod writes small files to your Factorio user folder (`script-output/touchdeck-bridge/`), the
  plugin watches them. Nothing goes to the internet.
- Every command is its own key binding of the mod (`Ctrl+Alt+Shift+…`). TouchDeck presses it in the
  Factorio window, the plugin waits for the game's answer and shows it on the button (e.g.
  “Speed 2×” or “Admins only”).

## The ready-made pages

Main page **Factorio** with status, research, speed, pause, save and big graphs for power and
evolution, plus folders for **Time**, **Research**, **Power**, **Game** and **Production**. When
Factorio comes to the front, TouchDeck switches to the page “Factorio”.

| Button | Tap | Double tap | Hold | Release |
| --- | --- | --- | --- | --- |
| Speed (main page) | 1× | 2× | 4× | back to 1× |
| Pause | pause on/off (red while paused) | – | – | – |
| Hold = 4× (Time) | – | – | 4× | back to 1× |
| Slower / Faster (Time) | half / double speed | – | – | – |
| Cancel (Research) | cancel research – only on the **second** press | – | – | – |
| #1 / #2 / #3 (Research) | queue the cheapest available research | – | – | – |
| Power (main page) | opens the page Power | – | – | – |

- **Power:** production by source (steam, turbines, solar, accumulators …) and consumption by
  building as stacked graphs of the last 10 minutes, plus production, consumption and load.
- **Production – you pick what you see:** 8 slots, each with a graph (production and consumption per
  minute). On a slot: **tap** = next item, **hold** = previous, **double tap** = automatic again
  (most produced items). The choice is kept.
- **Screen saver:** a card with status, research, power, planet, speed and evolution appears under
  the clock.
- **Messages:** “research finished” and “you died” appear at the bottom right of the main page – no
  pop-ups on the PC.
- The main page shows the **UTLogistics** button only while UTLogistics is active in the game.

## UTLogistics (optional)

With the mod [UTLogistics](https://mods.factorio.com/mod/UTLogistics), TouchDeck Bridge reads its
data – per planet: idle and moving trains, deliveries, stations, networks, alerts in full text and
requests without a train. The ready-made pages are **UTLogistics** (overview), **Stations**,
**Networks** and **Alerts**.

- **Planet** (button at the top): shows the planet you are on automatically. **Tap** = next planet,
  **hold** = all planets, **double tap** = automatic again.
- **Stations:** the UTL station window has a section **“TouchDeck”**: tick “Show on the TouchDeck”
  and pick a slot 1–8. The station then appears with its trains (here and on the way), supply and
  demand. The choice travels with blueprints. The UTL manager has a tab **“TouchDeck”** with all
  pinned stations.
- **Networks:** 8 slots for the networks of the planet. On a slot: **tap** = next network,
  **hold** = previous, **double tap** = automatic.
- Buttons open the UTL manager (also straight on its Alerts tab).

Without UTLogistics nothing happens – the pages then say “UTLogistics not active”.

## Your own buttons

Two actions in a row:

1. **Hotkey** (built-in action): e.g. `ctrl+alt+shift+p`, window `factorio`.
2. **Factorio › Wait for the game's answer**: waits up to 3 s and shows the answer. Without an answer
   it says why: game not running, Esc menu open or window not reachable.

| Ctrl+Alt+Shift+… | Command |
| --- | --- |
| P | Toggle pause |
| 1 / 2 / 3 / 4 | Speed 0.5× / 1× / 2× / 4× |
| N / M | Slower (½) / faster (×2) |
| S | Save (`_autosave-touchdeck`) |
| K | Screenshot |
| Q / W / E | Queue research suggestion 1 / 2 / 3 |
| X | Cancel research |
| H | Back to the player (leave remote view) |
| U | Write data again |
| G / A | UTL manager / UTL manager alerts (only with UTLogistics) |

More actions: *Production slot: choose item* (also by name, e.g. “Iron plate”), *UTLogistics: choose
planet*, *UTLogistics: choose network slot*, *UTLogistics: open its page*.

## Triggers (for events)

| Trigger | Data |
| --- | --- |
| Research finished / started | `{Event.Name}` (game language), `{Event.Intern}` |
| Rocket launched | `{Event.Anzahl}` |
| Player died | `{Event.Spieler}`, `{Event.Ich}` (ja/nein) |
| Evolution passed a 10 % step | `{Event.Prozent}`, `{Event.Flaeche}` |
| Command answered by the game | `{Event.Befehl}`, `{Event.Ok}` (ja/nein), `{Event.Meldung}` |
| Game connected / disconnected | – |
| UTLogistics: new alert | `{Event.Warnung}` |
| UTLogistics: request waiting without a train | `{Event.Anzahl}`, `{Event.Text}` |

The data names are German, like the value names (they stay the same in every language).

## Values

| Value | Content |
| --- | --- |
| `FStatus` | running · paused · halted · Factorio not running |
| `FSpielzeit`, `FTick` | play time (h:mm:ss), current tick |
| `FGeschwindigkeit`, `FPause` | e.g. `1`, `0.5` · on/off |
| `FForschung`, `FForschungProzent`, `FWarteschlange` | current research, 0–100, length of the queue |
| `FVorschlag1` … `FVorschlag3` | cheapest available research |
| `FStromErzeugung`, `FStromVerbrauch` | power of the network you stand in, e.g. `35.2 MW` |
| `FEvolution`, `FRaketen`, `FSpieler`, `FPlanet` | evolution in %, rockets, players online, planet or space platform |
| `FItem1` … `FItem8` | production slots, e.g. `Iron plate: 600/min` |
| `FMeldung` | last answer or message of the game |
| `FUtl…` | values for UTLogistics (trains, stations, networks, alerts …), see the value list in TouchDeck |

In the editor under *Live display › Plugin* there are also displays with graphs: research, speed,
evolution, power production (stacked by source), power consumption (by building), the 8 production
slots and, for UTLogistics, trains, goods, deliveries, stations and networks.

## Settings (all optional)

| Setting | Default |
| --- | --- |
| Folder of the mod files | empty = find automatically |
| Check files every … ms | 250 (while Factorio is running) |
| Without Factorio, check only every … ms | 3000 |
| No data for … seconds = not connected | 5 |

## Privacy

Everything stays on your computer. The plugin only reads the mod's files and checks whether Factorio
is running. It opens no network connection and writes nothing to disk.

## Limits

- **Single player – pause, Esc menu and research screen (technology tree):** the game stops
  completely, takes no keys and writes nothing. TouchDeck keeps the last values and shows “halted”.
  I do not know a way around this yet – ideas are welcome. In multiplayer the game keeps running in
  those screens.
- **Power** is the network you stand in. Separate networks are not added up.
- **Production** is the planet or platform you stand on.
- **No free text:** research only via the three suggestions. More is possible in the game with
  `/touchdeck …` or the command field (Ctrl+Alt+Shift+B).
- At the start of a game all research is “trigger research” (craft, mine …), which cannot be queued –
  so there are no suggestions yet.
- Multiplayer: every player gets the data only on their own computer. Pause, speed and save need
  admin rights.

## Build your own plugin or mod

The source is on GitHub:
[Marcel1853/touchdeck-plugins › plugins/factorio](https://github.com/Marcel1853/touchdeck-plugins/tree/main/plugins/factorio)
(the mod is the zip next to it). Load your own copy in TouchDeck under *Plugins › Develop*.

- `python3 tools/make_profile.py` builds the ready-made pages again.
- `python3 tests/test_plugin.py` tests the plugin against a simulated mod.
- `python3 tests/check_profile.py <touchdeck>/touchdeck-rs/server/catalog` checks the pages against
  the rules in the [TouchDeck source](https://github.com/Marcel1853/touchdeck).

License: MIT.
