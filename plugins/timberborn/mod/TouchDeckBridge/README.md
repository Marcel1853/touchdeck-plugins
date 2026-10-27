# TouchDeck Bridge (Timberborn mod)

**English** · [Deutsch](README.de.md)

Connects Timberborn with [TouchDeck](https://github.com/Marcel1853/touchdeck-plugins) – macro buttons
on your phone or tablet. The mod opens a small TCP server and gives the TouchDeck plugin “Timberborn”
the game's state: cycle, day, speed, weather with countdown, population, homeless, unemployed,
contaminated, supplies with “lasts … days”, notification history and active alerts. It runs commands
from the plugin (pause, speed, save, camera to notifications and alerts, message in the game) on the
game's main thread.

- Needs neither Harmony nor any other mod.
- Nothing goes to the internet. Default: only `127.0.0.1:34201` (this PC).

## Installation

Put this folder into `Documents/Timberborn/Mods/TouchDeckBridge` (on Linux with Proton:
`~/.local/share/Steam/steamapps/compatdata/1062090/pfx/drive_c/users/steamuser/Documents/Timberborn/Mods/`)
and enable it in the game's mod manager.

## Settings

On its first start the mod creates `settings.json` in its folder:

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | server on/off |
| `address` | `127.0.0.1` | `127.0.0.1` = only this PC; `0.0.0.0` = all network cards (TouchDeck on another PC) |
| `port` | `34201` | 1024–65535, enter the same in the plugin |
| `secret` | empty | secret word; required (at least 12 characters) if `address` is not `127.0.0.1` |
| `intervalMs` | `500` | how often the state is sent at most (200–5000) |

Changes apply within 2 seconds, no restart needed. The connection is not encrypted: use it only in
your own network.

## Building

`./build.sh` compiles `Code.dll` against the DLLs of your own Timberborn installation (path via
`TIMBERBORN_DIR`) and runs the protocol tests. `./build.sh install` also copies the mod into the mod
folder. Needs `dotnet` and `mono`, downloads nothing.

License: MIT.
