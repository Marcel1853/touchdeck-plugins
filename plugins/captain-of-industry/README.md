# Captain of Industry for TouchDeck

**English** · [Deutsch](README.de.md)

**Advanced TouchDeck plugin** for Captain of Industry 0.8. Shows live on your buttons what is easy
to miss in the game: whether there is enough power, whether workers are missing, how many months the
food lasts, whether unity is going down, whether research has stopped, which products are full or
running low, all active alerts (no fuel, storage full …) and a history of the latest alerts and
messages – including the ones that already vanished in the game. And it controls the game: pause,
speed, save, camera to alerts. Alerts, messages, power shortage, starvation, disease, finished
research and the new year trigger TouchDeck events.

It comes with the mod **TouchDeck Bridge** (folder `mod/TouchDeckBridge`). It needs no other mods
and adds no content to the game.

## How it works

```
Captain of Industry + mod (TCP server 127.0.0.1:34202) ◀── JSON lines ──▶ plugin (client) ──▶ values, live displays, triggers
TouchDeck button ──▶ plugin action ──▶ command to the mod ──▶ answer ("Game paused") as the button's message
```

- Captain of Industry loads mods only together with a save. The mod starts its TCP server on the
  first load and keeps it running until the game quits (in the main menu it reports "no game
  loaded"). By default it is only reachable from this PC (`127.0.0.1`).
- The mod reads the state in the game's sync step – where the game's own displays read it.
  Commands go into the game as normal inputs, like the buttons of the UI.
- All numbers come from the game itself: power and computing, unity, workers, settlements, food in
  months, disease, research, product statistics (produced minus used last month), the alert panel.

## Setup in four steps

1. **Load the plugin:** In TouchDeck turn on advanced mode (Plugins › Advanced), then install
   Plugins › Marketplace › **Captain of Industry** (or Plugins › Develop › load this folder).
   Confirm twice because it is an advanced plugin.
2. **Install the mod:** Click **"🧩 Install mod"** in the plugin card – TouchDeck finds the mod
   folder itself (Windows and Linux with Proton). By hand: unpack `TouchDeckBridge_0.1.1.zip` into
   the `Mods` folder of Captain of Industry:
   - Windows: `%APPDATA%\Captain of Industry\Mods\`
   - Linux (Steam with Proton):
     `~/.local/share/Steam/steamapps/compatdata/1594320/pfx/drive_c/users/steamuser/AppData/Roaming/Captain of Industry/Mods/`

   Afterwards there is a folder `TouchDeckBridge` with `manifest.json` and `TouchDeckBridge.dll`.
   Source and instructions of the mod:
   [github.com/Marcel1853/touchdeck-plugins › plugins/captain-of-industry/mod](https://github.com/Marcel1853/touchdeck-plugins/tree/main/plugins/captain-of-industry/mod/TouchDeckBridge)
3. **Import the pages:** In the plugin card or under "Ready-made pages" click
   **Captain of Industry (English)** or **Captain of Industry (Deutsch)** – same pages, only the
   texts differ. Import only one of them: importing only adds.
4. **Load a save** and switch on **TouchDeck Bridge** under "Mods" (also works for existing saves).
   The status button at the top left then shows "running".

Requirements: Captain of Industry 0.8 (tested with 0.8.7), TouchDeck 0.12, Python 3.8 or newer
(Linux; Windows is a very early alpha and untested). No settings needed: address `127.0.0.1`, port
`34202` and an empty secret match the mod's defaults.

## Two PCs: streaming PC and gaming PC

If TouchDeck runs on a different computer than the game (for example the streaming PC):

1. **On the gaming PC** edit `settings.json` in the mod folder (`…/Mods/TouchDeckBridge/settings.json`,
   created by the mod when a save is loaded for the first time):
   ```json
   {
     "enabled": true,
     "address": "0.0.0.0",
     "port": 34202,
     "secret": "a-long-secret-word",
     "intervalMs": 500
   }
   ```
   `0.0.0.0` means: on all network cards. The IP of one specific network card works too. Without a
   secret of at least 12 characters the server does not start then. The mod picks up saved changes
   within 2 seconds, also during the game.
2. **On the streaming PC** in the plugin settings: **Address** = IP or host name of the gaming PC
   (e.g. `192.168.178.20` or `gaming-pc.local`), **Port** = the same as in the mod, **Secret** = the
   same.
3. If a firewall runs on the gaming PC: allow the port (TCP 34202) in your own network.

The connection is **not encrypted**: use it only in your own network, never expose it to the
internet (no port forwarding in the router).

## The ready-made pages

Main page **Captain of Industry** (4 × 6) with the most important live displays and six folders,
created like "Create folder here" in the editor (own page "Captain of Industry › …" with Back at the
top left): **Alerts**, **History**, **Power**, **Population**, **Products**, **Game**. When the game
comes to the front, TouchDeck switches to the main page once per game start (two events: Linux with
Proton and Windows). There are deliberately no notifications on the PC: what matters, the buttons
show in **red**.

| Page | What is on it |
| --- | --- |
| Main page | status, year and month, speed, pause, save, power with load bar, workers, food, alerts, unity, research, newest history entry |
| Alerts | up to 8 active alerts, critical first, with the number affected |
| History | the last 8 new alerts and messages (research done, refugees …), newest first |
| Power | power, demand, computing, unity with change per month, research |
| Population | population, homeless, free homes, workers, food, starving, disease, the two most important alerts |
| Products | 8 products with fill bar and trend per month: first the ones pinned in the game (📌), then the largest stock |
| Game | connection, speed 1–3, slower/faster, pause on/resume, "hold = short pause", quick save, save with year and month |

### What turns red

| Display | Red when … |
| --- | --- |
| Power | demand is higher than generation |
| Computing | demand is higher than capacity |
| Unity | it went down last month |
| Workers | workers are missing |
| Population | someone is homeless |
| Food | it lasts less than 3 months or people are starving |
| Disease | a disease is going around |
| Alerts | there are active warnings or critical alerts (not the green success ones) |
| Product 1–8 | the storage is full or the product runs out within 2 months at the current use |
| History 1–8 | (highlighted) the entry is from this month |
| Research | (blue) research is running; "No research running" means: the lab is idle |

### What the buttons do

| Button | Tap | Double tap | Hold |
| --- | --- | --- | --- |
| Status | fetch state | – | – |
| Speed | one level faster | one level slower | back to speed 1 |
| Pause | pause on/off (`{COIPause}` shows the real state) | – | – |
| Save | quick save "TouchDeck-Quicksave" | – | save "TouchDeck year ‹Y› month ‹M›" |
| Alerts | camera to the most important alert | – | – |
| Alert 1–8 | camera to the next one affected (each tap the next) | – | – |
| History 1–8 | camera there if the alert has a place | – | – |
| Faster (Game) | one level | – | one level every 0.6 s |
| Hold = short pause (Game) | – | – | pause, resumes on **release** |

Alerts, History, Power, Population and Products fetch the state once when opened.

## Actions, triggers, values

**Actions** (`plugin:captain-of-industry:…`): `pause` (toggle/on/off), `speed` (set level, faster,
slower – levels like the speed buttons in the game), `save` (name, empty = "TouchDeck-Quicksave"),
`alert` (camera to alert no. 1–8, the next one affected each time), `history` (camera to history
no. 1–8), `refresh`.

**Triggers**: `notification` (Text, Kind: `critical`/`warning`/`success`), `message` (Text, Kind:
`message`, `research`, `refugees`, `explored`, `battle`), `research_finished` (Name), `power_short`
(Capacity, Demand), `food_low` (Months), `starving` (Months), `disease` (Name), `new_year` (Year),
`game_over` (Text), `connected`, `disconnected`. Data in the event as `{Event.Text}`, `{Event.Name}`
etc. (German keys like `{Event.Jahr}` work too).

**Values** (same names in both languages): `COIJahr` (year), `COIMonat` (month), `COIDatum`,
`COITempo`, `COIPause`, `COIStrom`, `COIStromBedarf`, `COIStromKapazitaet` (power in kW),
`COIRechnen`, `COIRechnenKapazitaet` (computing in TFLOPS), `COIEinheit`, `COIEinheitMonat` (unity),
`COIArbeiterFrei` (free workers, negative = missing), `COIEinwohner`, `COIObdachlos`,
`COIWohnraumFrei`, `COINahrungMonate`, `COIHunger`, `COIKrankheit`, `COIForschung`,
`COIForschungProzent`, `COIWarnungen`, `COIUngelesen`, `COIWarnung1`–`COIWarnung8`,
`COIVerlauf1`–`COIVerlauf8`, `COIStatus`, `COIVerbunden`, `COIImSpiel` and for every product in
storage `COIWare_<Id>` (e.g. `COIWare_IronOre`, `COIWare_Diesel`).

**Live displays**: `status`, `date`, `speed` (bar), `power` (bar), `computing` (bar), `unity`
(bar), `workers`, `population`, `food` (bar), `health`, `research` (bar), `alerts`, `good1`–`good8`
(bar), `note1`–`note8`, `alert1`–`alert8`.

## Settings

| Plugin | Mod (`settings.json` in the mod folder) |
| --- | --- |
| Address (default `127.0.0.1`, host name too) | `address` (default `127.0.0.1`, `0.0.0.0` = all network cards) |
| Port (default `34202`) | `port` (1024–65535) |
| Secret | `secret` |
| Wait for the answer (5 s) | `enabled` (server on/off), `intervalMs` (send interval, 500 ms) |

Why a separate file instead of the mod settings in the game? Captain of Industry stores those in the
save – but address and port belong to the PC, not to the save.

## Privacy and security

- Everything stays on your PC or in your network. Nothing goes to the internet, no telemetry.
- Even with `127.0.0.1` every program on this PC can send commands to the mod. If you don't want
  that, enter the same secret in the mod and the plugin.
- Remote access only with a secret (at least 12 characters) and only in your own network – see above.

## Tests

```
python3 tests/test_plugin.py         # plugin against a fake mod (state, power, products, alerts, history, commands, timeout …)
python3 tests/test_real_server.py    # plugin against the mod's real C# server (needs dotnet + mono)
python3 tests/check_profile.py ../../../touchdeck-rs/server/catalog   # pages against TouchDeck's rules
python3 tools/make_profile.py        # creates both page files (English and German)
mod/TouchDeckBridge/build.sh         # build the mod + protocol tests + ZIP
python3 tests/fake_mod.py            # fake mod to try the pages without the game
```

License: MIT.
