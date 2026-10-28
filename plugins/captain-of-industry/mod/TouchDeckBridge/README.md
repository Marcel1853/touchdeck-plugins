# TouchDeck Bridge (Captain of Industry mod)

**English** · [Deutsch](README.de.md)

Connects Captain of Industry to [TouchDeck](https://github.com/Marcel1853/touchdeck-plugins) – macro
buttons on your phone or tablet. The mod opens a small TCP server and gives the TouchDeck plugin
"Captain of Industry" the state of the game: date, speed, power, computing, unity, free or missing
workers, population, homeless, food in months, disease, research, products with trend, active alerts
and a history of new alerts and messages. Commands from the plugin (pause, speed, save, camera to
alerts) run on the game's main thread.

- Needs no other mods, adds no content to the game – can be added to existing saves and removed
  again.
- Nothing goes to the internet. Default: only `127.0.0.1:34202` (this PC).

## Installation

Easiest from TouchDeck: plugin card "Captain of Industry" › "🧩 Install mod".

By hand: put the folder `TouchDeckBridge` (from `TouchDeckBridge_0.1.1.zip`) into the mods folder:

- Windows: `%APPDATA%\Captain of Industry\Mods\TouchDeckBridge`
- Linux (Steam with Proton):
  `~/.local/share/Steam/steamapps/compatdata/1594320/pfx/drive_c/users/steamuser/AppData/Roaming/Captain of Industry/Mods/TouchDeckBridge`

Then switch on "TouchDeck Bridge" under "Mods" when loading or starting a game.

## Settings

When a save is loaded for the first time, the mod creates `settings.json` in its folder:

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | server on/off |
| `address` | `127.0.0.1` | `127.0.0.1` = only this PC; `0.0.0.0` = all network cards (TouchDeck on another PC) |
| `port` | `34202` | 1024–65535, enter the same in the plugin |
| `secret` | empty | secret; required (at least 12 characters) if `address` is not `127.0.0.1` |
| `intervalMs` | `500` | how often the state is sent at most (200–5000) |

Changes apply within 2 seconds, without restarting. The connection is not encrypted: use it only in
your own network. The mod's messages are in the game's log (`…/Captain of Industry/Logs/`, lines with
"[TouchDeck Bridge]").

## Building

`./build.sh` compiles `TouchDeckBridge.dll` against the DLLs of your own Captain of Industry
installation (path via `COI_ROOT`), runs the protocol tests and packs
`../../TouchDeckBridge_<version>.zip`. `./build.sh install` also copies the mod into the mods folder
(`COI_MODS`). Needs `dotnet` and `mono`, downloads nothing.

License: MIT.
