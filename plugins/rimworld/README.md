# RimWorld for TouchDeck

**English** · [Deutsch](README.de.md)

**Advanced TouchDeck plugin** for RimWorld 1.6. Shows date, speed, mood, silver, research, threat
and more live on your buttons and controls the game: pause, speed 1–4, save, screenshot, draft all,
camera to colonists or the last letter, in-game messages, main tabs and research. Letters, raids,
deaths, mental breaks and finished research trigger TouchDeck events.

It comes with the RimWorld mod **TouchDeck Bridge** (folder `mod/TouchDeckBridge`, needs Harmony).

## How it works

```
RimWorld + mod (TCP server 127.0.0.1:34200) ◀──── JSON lines ────▶ plugin (client) ──▶ values, live displays, triggers
TouchDeck button ──▶ plugin action ──▶ command to the mod ──▶ answer ("Game paused") as the button's message
```

- When the game starts, the mod opens a small TCP server, by default reachable from this PC only
  (`127.0.0.1`). The plugin connects, reconnects by itself after a drop and receives the state
  whenever something changes (a heartbeat at least every 5 s).
- Commands run on the game's main thread – also while paused and in the main menu (there they
  answer "No game loaded").
- No key presses, no launch options, nothing to set up in RimWorld.

## Setup in four steps

1. **Install and enable the mod:** subscribe to Harmony in the Steam Workshop. Put the folder
   `mod/TouchDeckBridge` (or the unpacked `TouchDeckBridge_0.2.0.zip`) into
   `…/steamapps/common/RimWorld/Mods/`. In RimWorld, enable "TouchDeck Bridge" under **Mods**
   after Harmony and restart.
   **Easier:** do step 2 first, then click “🧩 Install mod” in the plugin card – TouchDeck finds
   the mod folder itself (Linux, Windows and Proton).
2. **Load the plugin:** turn on advanced mode in TouchDeck (Plugins › Advanced), then install
   **RimWorld** under Plugins › Marketplace (or load this folder under Plugins › Develop).
   Confirm twice, because it is an advanced plugin.
3. **Import the pages:** on the plugin card or under "Ready-made pages", click
   **RimWorld (English)** or **RimWorld (Deutsch)** – same pages, only the texts differ. Import
   only one of them: importing only adds, it never overwrites.
4. **Start the game** and load a colony – done. The status button at the top left shows "running".

Requirements: RimWorld 1.6 with Harmony, TouchDeck 0.12, Python 3.8 or newer (Linux; Windows is a very early alpha and untested). No settings needed:
address `127.0.0.1`, port `34200` and an empty secret match the mod's defaults.

## The ready-made pages

Main page **RimWorld** (4 × 6) with live displays and four folders, created like "Create folder
here" in the editor (own page "RimWorld › …" with Back at the top left): **Time**, **Colonists**,
**Messages**, **Game**. When RimWorld comes to the front, TouchDeck switches to the page "RimWorld"
once per game start (event "RimWorld in front"; turn off "only the first time" if it should switch
every time). A raid or a colonist's death shows a notification on the PC.

### What each button does

| Button | Tap | Double tap | Hold | Display |
| --- | --- | --- | --- | --- |
| Status (main page) | – | – | – | connection and state, green in game |
| Date (main page) | – | – | – | in-game date and hour |
| Speed | one step faster | one step slower | back to 1× | speed, on = running |
| Pause | pause on/off | – | – | `{RWPause}`: on = paused (▶️, brown) |
| Save | quick save "TouchDeck-Quicksave" | – | save "TouchDeck ‹date› ‹hour›" | – |
| Mood | – | – | – | lowest mood as a bar, red below 25 % |
| Research | open/close research tab | – | – | research with bar |
| Silver | – | – | – | silver in storage |
| Threat | camera to the last letter | open the letter | – | red ⚔️ while the game reports danger |
| Draft | all in if not all are drafted, otherwise all out | release all | draft all | "2/5 drafted", red = all drafted |
| Next | next colonist (camera + selection) | previous | step on every 0.8 s | – |
| Letter `{RWBrief}` | camera to the last letter | open the letter | – | title of the last letter |
| 1× to 4× (Time) | set speed (template "set speed"), 4× only in dev mode | – | – | – |
| Slower / Faster (Time) | one step | – | Faster: one step every 0.6 s | – |
| Pause / Resume (Time) | pause / resume | – | – | – |
| Hold = short pause (Time) | – | – | pause, resumes on **release** | – |
| Colonist 1–8 (Colonists) | camera to colonist no. (template "jump to colonist") | – | – | name from the colonist bar |
| Draft all / Release all (Colonists) | as labelled | – | – | – |
| Work, Schedule, Assign, Animals, Research, World, Architect, Menu, Quests, History, Factions | open/close main tab | – | – | – |
| Event 1–8 (Messages) | camera to where it happened | open the letter | – | the last 8 letters from History › Messages (also dismissed ones), newest first: title and age, red for threats and deaths |
| Older: open History (Messages) | open the History window | – | – | – |
| Quick save / Save with date / Screenshot (Game) | as labelled, screenshot path as message | – | – | – |
| Fetch state, Connected (Game) | fetch the state right now | – | – | connection |

The page **Colonists** fetches the state once when opened (page logic "page opened").

**Why no toggles?** A toggle keeps its state inside TouchDeck. If you pause with the space bar in
the game or draft colonists there, it would be wrong. Pause, draft and threat therefore show the
game's real state through live displays with the "on" look.

**Why no slider for the speed?** Sliders in TouchDeck only control volume, microphone, OBS or a
command (`store.rs`, `live.json`), not plugin values. RimWorld has only four speeds anyway: plus/minus
and step buttons are more precise.

**`deck.setLook`** is not used: buttons get new IDs on import, so the plugin could not find them
reliably. The red colour on danger comes from the live display "threat" (on = red).

## Actions, triggers, values

**Actions** (`plugin:rimworld:…`): `pause` (toggle/on/off), `speed` (set 1–4, faster, slower),
`save` (name, empty = quick save; in permadeath mode always the game's own save), `screenshot`,
`draft` (toggle/all/none), `jump` (colonist no.), `cycle` (next/previous), `letter` (camera to the
last letter or to event no. 1–8 / open it), `message` (text with placeholders, kind), `tab` (main tab), `research`
(choose research by name), `refresh`.

**Triggers**: `letter` (Title, Kind, Text, Threat), `raid` (letter with a big threat),
`colonist_died` (Name), `mental_break` (Name, Kind), `research_finished` (Name, Intern),
`connected`, `disconnected`. Event data is available as `{Event.Title}`, `{Event.Name}` etc.
(German keys like `{Event.Titel}` work too). The mod reports events with the same cause within 4 s
only once.

**Values** (names are the same in both languages, the plugin sets exactly these): `RWDatum` (date),
`RWUhrzeit` (hour), `RWTempo` (speed 0–4), `RWPause` (on/off), `RWKolonisten` (colonists),
`RWGefangene` (prisoners), `RWStimmungMin` / `RWStimmungSchnitt` (lowest / average mood),
`RWEingezogen` (drafted), `RWSilber`, `RWStahl` (steel), `RWKomponenten` (components),
`RWMedizin` (medicine), `RWNahrung` (food), `RWForschung` / `RWForschungProzent` (research),
`RWWetter` (weather), `RWTemperatur`, `RWKarte` (map), `RWKolonie` (colony), `RWSpielstand` (save
game), `RWBedrohung` (threat), `RWBrief` (last letter), `RWKolonist1`–`RWKolonist8`, `RWEreignis1`–`RWEreignis8` (events from the history), `RWStatus`,
`RWVerbunden` (connected yes/no), `RWImSpiel` (in game yes/no). Their texts (e.g. "paused",
"yes") follow the system language.

**Live displays**: `status`, `date`, `speed`, `mood` (bar), `research` (bar), `silver`, `danger`,
`draft`, `event1`–`event8` (events from the history; on = threat or death).

## Settings

| Plugin | Mod (Options › Mod settings › TouchDeck Bridge) |
| --- | --- |
| Address (default `127.0.0.1`) | Address (default `127.0.0.1`, `0.0.0.0` = all network cards) |
| Port (default `34200`) | Port (1024–65535) |
| Secret | Secret |
| Wait for the answer (5 s) | Server on/off, send interval (500 ms) |

Changed mod settings apply immediately (the server restarts); no game restart needed.

## Privacy and security

- Everything stays on your PC: plugin and mod talk via `127.0.0.1`. Nothing goes to the internet,
  there is no telemetry.
- Even with `127.0.0.1`, any program on this PC can send commands to the mod. If you don't want
  that, enter the same secret in mod and plugin.
- **Remote access** (mod on another computer): set the mod's address to `0.0.0.0` or the IP of the
  network card, and the plugin's address to the IP of the gaming PC. Then a secret of at least
  12 characters is required, otherwise the server does not start. The connection is **not
  encrypted**: use it only in your own network, never on the open internet (no port forwarding in
  the router).

## Tests

```
python3 tests/test_plugin.py         # plugin against a fake mod (hello, state, commands, timeout, drop …)
python3 tests/test_real_server.py    # plugin against the mod's real C# server (needs dotnet + mono)
python3 tests/check_profile.py ../../../touchdeck-rs/server/catalog   # pages against TouchDeck's rules
python3 tools/make_profile.py        # builds both page files (English and German)
mod/TouchDeckBridge/build.sh         # builds the mod + protocol tests (JSON, queue, TCP server)
python3 tests/fake_mod.py            # fake mod to try the pages without the game
```

License: MIT.
