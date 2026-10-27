# Timberborn for TouchDeck

**English** · [Deutsch](README.de.md)

**Advanced TouchDeck plugin** for Timberborn 1.1. Shows live on your buttons what is easy to miss in
the game: when the next drought or badtide arrives, how many days water and food last, homeless,
unemployed and contaminated beavers, full storage, the notification history and all active alerts.
It also controls the game: pause, speed 1–3, save, camera to notifications and alerts, messages in
the game. Hazards, new notifications, births and deaths fire TouchDeck events.

It comes with the Timberborn mod **TouchDeck Bridge** (folder `mod/TouchDeckBridge`). The mod needs
neither Harmony nor any other mod.

## How it works

```
Timberborn + mod (TCP server 127.0.0.1:34201) ◀──── JSON lines ────▶ plugin (client) ──▶ values, live displays, triggers
TouchDeck button ──▶ plugin action ──▶ command to the mod ──▶ answer (“Game paused”) as the button's message
```

- When the game starts, the mod opens a small TCP server, by default only on this PC (`127.0.0.1`).
  The plugin connects, reconnects by itself and receives the state whenever something changes
  (a heartbeat at least every 5 s).
- Commands run on the game's main thread – also while paused and in the main menu (there they answer
  “No game loaded”).
- All numbers come from the game itself: weather from the weather service, population from the
  population statistics, “lasts … days” from the goods statistics (average of the last three days),
  alerts from the alert panel at the top right.
- The plugin only tells you the kind of the next hazard once the game announces it (3 days before).
  Until then it shows “?”.

## Setup in four steps

1. **Install the mod:** Put the folder `mod/TouchDeckBridge` (or `TouchDeckBridge_0.1.0.zip`
   unpacked) into Timberborn's mod folder: `Documents/Timberborn/Mods/`. On Linux with Proton (Steam)
   that is
   `~/.local/share/Steam/steamapps/compatdata/1062090/pfx/drive_c/users/steamuser/Documents/Timberborn/Mods/`.
   Start Timberborn and enable “TouchDeck Bridge” in the mod manager.
2. **Load the plugin:** In TouchDeck, turn on advanced mode (Plugins › Advanced), then install
   Plugins › Marketplace › **Timberborn** (or Plugins › Develop › load this folder). Confirm twice,
   because it is an advanced plugin.
3. **Import the pages:** In the plugin card or under “Ready-made pages”, click
   **Timberborn (English)** or **Timberborn (Deutsch)** – same pages, only the texts differ. Import
   only one of them: importing only adds, it never overwrites.
4. **Load a save** – done. The status button at the top left shows “running”.

Requirements: Timberborn 1.1, TouchDeck 0.12, Python 3.8 or newer (Linux; Windows is a very early
alpha and untested). No settings required: address `127.0.0.1`, port `34201` and an empty secret
match the mod's defaults.

## Two PCs: streaming PC and gaming PC

If TouchDeck runs on a different computer than the game (for example on your streaming PC):

1. **On the gaming PC**, edit `settings.json` in the mod folder
   (`…/Mods/TouchDeckBridge/settings.json`, created by the mod on its first start):
   ```json
   {
     "enabled": true,
     "address": "0.0.0.0",
     "port": 34201,
     "secret": "a-long-secret-word",
     "intervalMs": 500
   }
   ```
   `0.0.0.0` means all network cards; the IP of one specific network card works too. Without a
   secret of at least 12 characters the server will not start. The mod picks up saved changes within
   2 seconds, even while playing.
2. **On the streaming PC**, in the plugin settings: **Address** = IP or host name of the gaming PC
   (e.g. `192.168.178.20` or `gaming-pc.local`), **Port** = the same as in the mod, **Secret** = the
   same.
3. If a firewall runs on the gaming PC: allow the port (TCP 34201) in your local network.

The connection is **not encrypted**: use it only in your own network, never expose it to the
internet (no port forwarding in your router).

## The ready-made pages

Main page **Timberborn** (4 × 6) with the most important live displays and seven folders, built like
“Create folder here” in the editor (own page “Timberborn › …” with Back at the top left): **Time**,
**Weather**, **Beavers**, **Supplies**, **Notifications**, **Alerts**, **Game**. When Timberborn
comes to the front, TouchDeck switches to the page “Timberborn” once per game start (two events: Linux
with Proton and Windows; turn off “only the first time” to switch every time). When the game
announces a hazard, when it starts or when a beaver dies, you get a notification on the PC.

| Page | What's on it |
| --- | --- |
| Main page | Status, cycle/day/time (on = night), speed, pause, save, weather countdown with bar, water and food with “lasts … days”, alerts, beavers, homeless, unemployed, newest notification |
| Time | Speed 1–3, slower/faster, pause/resume, “hold = short pause” |
| Weather | Countdown to the hazard, its kind (once announced), duration, days left, water, food |
| Beavers | Population, well-being, homeless/free beds, unemployed/free jobs, contaminated, kids, bots, science, the two largest alerts |
| Supplies | Water, food, science and twelve goods with fill bars and trend per day (on = storage full) |
| Notifications | Notification history: the last 8 notifications, newest first, today's highlighted |
| Alerts | Up to 8 active alerts with the number affected |
| Game | Connection, settlement and faction, quick save, save with cycle and day, greeting to the game |

### What the buttons do

| Button | Tap | Double tap | Hold | Display |
| --- | --- | --- | --- | --- |
| Status | fetch state | – | – | connection and state, green in game |
| Speed | one step faster | one step slower | back to speed 1 | speed, on = running |
| Pause | pause on/off | – | – | `{TBPause}`: on = paused (▶️, brown) |
| Save | quick save “TouchDeck-Quicksave” | – | save “TouchDeck cycle ‹C› day ‹D›” | – |
| Weather | – | – | – | “Hazard in 5.5 days” or “Drought: 3 days left”, red from 3 days before |
| Water / Food | – | – | – | stock and how many days it lasts, red below 3 days |
| Alerts | camera to the largest alert | – | – | count and largest alert, red when there are any |
| Notification 1–8 | camera to the beaver or building it is about | – | – | text, cycle and day; highlighted if from today |
| Alert 1–8 | camera to the next one affected (each tap the next) | – | – | text and count |
| Speed 1–3 (Time) | set speed (template “set speed”) | – | – | – |
| Faster (Time) | one step | – | one step every 0.6 s | – |
| Hold = short pause (Time) | – | – | pause, resumes on **release** | – |

Weather, Beavers, Supplies, Notifications and Alerts fetch the state once when opened (page logic
“page opened”).

**Why no toggles?** A toggle remembers its state in TouchDeck. If you pause with the space bar in the
game, it would be wrong. Pause, hazard and alerts therefore show the game's real state through live
displays with an “on” look.

## Actions, triggers, values

**Actions** (`plugin:timberborn:…`): `pause` (toggle/on/off), `speed` (set 1–3, faster, slower),
`save` (name, empty = “TouchDeck-Quicksave”), `notification` (camera to notification no. 1–8),
`alert` (camera to alert no. 1–8, the next one affected each time), `message` (text with
placeholders, normal or warning), `refresh`.

**Triggers**: `notification` (Text, Cycle, Day), `hazard_approaching` (Kind, Name, Days),
`hazard_started` (Kind, Name, Days), `hazard_ended`, `cycle_started` (Cycle), `beaver_born`,
`character_died` (Name, Age), `alert` (Text – exactly as in the alert panel), `game_over`,
`connected`, `disconnected`. Event data as `{Event.Name}`, `{Event.Days}` etc. (German keys like
`{Event.Tage}` work too). The kind is `drought` or `badtide`.

**Values** (same names in both languages): `TBZyklus` (cycle), `TBTag` (day), `TBUhrzeit` (time),
`TBDatum`, `TBTempo` (0–3), `TBPause` (on/off), `TBWetter` (weather), `TBGefahrIn` (days until the
hazard), `TBGefahrArt` (its kind), `TBGefahrRest` (days left), `TBGefahrDauer` (duration), `TBBiber`
(beavers), `TBErwachsene`, `TBKinder`, `TBBots`, `TBBevoelkerung`, `TBObdachlos` (homeless),
`TBBettenFrei`, `TBArbeitslos` (unemployed), `TBStellenFrei`, `TBVerseucht` (contaminated),
`TBZufriedenheit` (well-being), `TBWissenschaft` (science), `TBWasser`, `TBWasserTage`, `TBNahrung`,
`TBNahrungTage`, `TBWarnungen`, `TBFraktion`, `TBSiedlung`, `TBMeldung1`–`TBMeldung8`,
`TBWarnung1`–`TBWarnung8`, `TBStatus`, `TBVerbunden`, `TBImSpiel`, and for every good in storage
`TBWare_<Id>` (e.g. `TBWare_Log`, `TBWare_Berries` – the IDs are in the game's blueprints).

**Live displays**: `status`, `date`, `speed`, `weather` (bar), `population`, `homeless`,
`unemployed`, `contaminated`, `wellbeing`, `science`, `water`, `food`, `alerts`, `good_<Id>` for
Log, Plank, Gear, TreatedPlank, MetalBlock, ScrapMetal, Biofuel, Dirt, Explosives, Paper, Book,
PunchCard (bar), `note1`–`note8`, `alert1`–`alert8`.

## Settings

| Plugin | Mod (`settings.json` in the mod folder) |
| --- | --- |
| Address (default `127.0.0.1`, host names work too) | `address` (default `127.0.0.1`, `0.0.0.0` = all network cards) |
| Port (default `34201`) | `port` (1024–65535) |
| Secret | `secret` |
| Wait for an answer (5 s) | `enabled` (server on/off), `intervalMs` (send interval, 500 ms) |

## Privacy and security

- Everything stays on your PC or in your network. Nothing goes to the internet, there is no telemetry.
- Even with `127.0.0.1`, any program on this PC can send commands to the mod. If you don't want that,
  enter the same secret in the mod and the plugin.
- Remote access only with a secret (at least 12 characters) and only in your own network – see above.

## Tests

```
python3 tests/test_plugin.py         # plugin against a fake mod (state, weather, supplies, history, commands, timeout …)
python3 tests/test_real_server.py    # plugin against the mod's real C# server (needs dotnet + mono)
python3 tests/check_profile.py ../../../touchdeck-rs/server/catalog   # pages against TouchDeck's rules
python3 tools/make_profile.py        # writes both page files (English and German)
mod/TouchDeckBridge/build.sh         # build the mod + protocol tests (JSON, queue, TCP server)
python3 tests/fake_mod.py            # fake mod to try the pages without the game
```

License: MIT.
