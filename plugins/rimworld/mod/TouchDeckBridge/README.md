# TouchDeck Bridge (RimWorld mod)

**English** · [Deutsch](README.de.md)

Connects RimWorld to [TouchDeck](https://github.com/Marcel1853/touchdeck-plugins) (phone or tablet as
a control panel). The mod opens a small TCP server; the TouchDeck plugin `rimworld` connects to it,
shows the colony's state live and sends commands.

- **Version:** 0.1.0 · **Game:** RimWorld 1.6 (built and checked against 1.6.4871 rev598)
- **Needs:** Harmony (`brrainz.harmony`), loaded before this mod
- **packageId:** `Marcel171297.TouchDeckBridge` · **Author:** Marcel171297 · **License:** MIT

## Features

- **State** (at most every 500 ms, only on change, otherwise a heartbeat every 5 s): date and hour,
  tick, speed and pause, free colonists and prisoners of the current map, lowest and average mood,
  drafted colonists, names in the order of the colonist bar, silver, steel, components, medicine,
  food, weather and outdoor temperature, colony, map, save game, current research with percent,
  danger level (as used for the game's music: calm/danger/high), last letter. In the main menu
  only `inGame: false`.
- **Commands:** pause (toggle/on/off), speed 1–4 and faster/slower (4 only in dev mode, as in the
  game), save (name or quick save; in permadeath mode always the game's own save), screenshot (path
  in the answer), draft/release all, camera to colonist no. N, next/previous colonist, camera to the
  last letter or open it, show a message at the top left, open/close main tabs, choose research by
  name.
- **Events:** every letter (title, type, shortened text, threat), death of a colonist, mental break
  (name, kind), finished research. Events with the same cause within 4 s are reported only once.

## Setup

1. Subscribe to Harmony in the Workshop.
2. Copy this folder `TouchDeckBridge` into `…/steamapps/common/RimWorld/Mods/`.
3. Enable it in the game under **Mods** (after Harmony) and restart.
4. Optional: **Options › Mod settings › TouchDeck Bridge** – server on/off, address, port, secret,
   send interval. Changes apply immediately, the server restarts by itself.

Then set up the TouchDeck plugin `rimworld` (see the [plugin's README](../../README.md)).

## Building

```
./build.sh            # builds 1.6/Assemblies/TouchDeckBridge.dll and runs the protocol tests
./build.sh install    # also copies it to RimWorld/Mods/TouchDeckBridge
```

Needs the .NET SDK (tested with 8.0) and Mono (for the net472 references in
`/usr/lib/mono/4.7.2-api` and to run the tests). It builds against the DLLs of your own RimWorld
installation and Harmony from the Workshop – so the names match the version you play, and nothing
has to be downloaded. Other paths: `RIMWORLD_DIR=… HARMONY_DIR=… ./build.sh`. To build without an
installed game, replace the references in `TouchDeckBridge.csproj` with the NuGet packages
`Krafs.Rimworld.Ref` (1.6.*) and `Lib.Harmony` (`ExcludeAssets=runtime`).

Source layout:

| Folder | Contents |
| --- | --- |
| `Source/TouchDeckBridge/Protocol/` | JSON, protocol, command queue, TCP server – no RimWorld types |
| `Source/TouchDeckBridge/Game/` | thin adapters: mod settings, main-thread tick, state, commands, Harmony patches |
| `Source/Tests/` | tests of the protocol parts (run on Mono, without the game) |

## How the mod treats the game

- **Main thread:** the network thread never touches the game state. Commands go into a queue; an
  invisible Unity object processes them on the main thread every frame (at most 8 per frame) and
  also collects the state there. This also works while paused and in the main menu – unlike a
  `GameComponent`, which does not exist in the main menu (commands would then never be answered).
- **No load per tick:** the state is collected at most every 250–5000 ms (setting), only from
  existing lists and counters (`FreeColonists`, `resourceCounter`, colonist bar). Nothing is
  collected while no plugin is connected.
- **Harmony only for events:** `LetterStack.ReceiveLetter`, `Pawn.Kill`,
  `MentalStateHandler.TryStartMentalState`, `ResearchManager.FinishProject` and, for the save game's
  name, `GameDataSaveLoader.SaveGame`/`LoadGame`. Each patch is applied separately; if a method is
  missing in another version, only that event is dropped (warning in the log).
- **Errors** are caught and written to the log; they never crash the game.

## Security

- The default is `127.0.0.1`: only programs on this PC can reach the server. **That still means
  every program on this PC** – if you don't want that, set a secret (the same in mod and plugin).
- Any other address (e.g. `0.0.0.0` for all network cards) requires a secret of at least
  12 characters; without one the server does not start and the settings window shows a warning.
  The secret is sent in the plugin's hello and compared in constant time.
- **Unencrypted.** Use it only in your own network, never on the open internet.
- At most 4 connections, lines over 64 KB are dropped, at most 64 queued commands.

## Multiplayer

Multiplayer (e.g. with the "Multiplayer" mod) is not a goal. Commands change your own game directly
and do not go through a multiplayer mod's synchronisation: pause, speed, draft and research would
make the games drift apart (desync). Only displays, camera, screenshot and messages would be
harmless – this is not tested.

## Known limits

- Speed 4 (ultrafast) only exists in RimWorld's dev mode; otherwise the command answers with a hint.
- "Save" reports "saved" once the game's save action has finished. If saving fails inside the game
  itself (e.g. disk full), RimWorld shows its own error.
- The screenshot is written at the end of the frame; the path in the answer is still correct.
- The mod only knows the save game's name after saving or loading in this session.
- Colonist no. N follows the colonist bar (all maps, including caravans); colonists and mood in the
  state only count the current map.
- IPv4 only.

## Checking in the game (test list)

Anything that only runs in the game is not tested automatically. This is how you check it (plugin
connected, page "RimWorld" open):

| Step | Expected |
| --- | --- |
| Start the game, stay in the **main menu** | Log: "[TouchDeck Bridge] listening on 127.0.0.1:34200". Status button "Main menu (no game loaded)", values "–". Press Pause → message "No game loaded". |
| Open the mod settings | "Server running on 127.0.0.1:34200, connected: 1". |
| Load a colony | Status "running"; date, silver, mood and research appear within ~1 s. |
| **Space bar in the game** (pause) | Pause button turns brown with ▶️, speed display "paused". |
| Pause button on the deck | Game pauses/resumes, message on the button. |
| Speed tap / double tap / hold | faster / slower / 1×; while paused, speed unpauses. |
| Speed 4× without dev mode | Message "Speed 4 only exists in RimWorld's dev mode", speed stays. |
| **Game paused**, then Draft, Colonist 1, message | Everything works while paused too (commands run per frame, not per tick). |
| Tap Draft | All draftable colonists drafted, button red "3/3 drafted"; again → all released. |
| Release one colonist by hand in the game | Draft button turns dark again ("2/3"). |
| Colonist 1–8 | Camera jumps and selects; names match the bar at the top. |
| Message button | Text appears at the top left; "threat" with a warning sound. |
| Tap Save | Loading screen "Saving", then "Saved as TouchDeck-Quicksave"; save shows up in the load menu. |
| Screenshot | Message with path, file in `~/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios/Screenshots/`. |
| Research button | Research window opens/closes. |
| Dev mode › trigger a raid | Letter arrives; event "raid" → PC notification; Threat turns red; letter button shows the title; tap Threat → camera to the location. |
| Dev mode › kill a colonist | Notification "… has died", colonist count goes down. |
| Dev mode › mental break | Trigger `mental_break` (e.g. in TouchDeck's event log). |
| Dev mode › finish research | Trigger `research_finished`, research display changes. |
| **Load a game while connected** | Briefly "main menu", then the values of the new save; "save game" shows its name; no errors in the log. |
| Back to the main menu | Values "–", connection stays ("Connected: yes"). |
| Mod settings: change the port, close | Log: server restarted on the new port; the plugin loses the connection until the same port is set there. |
| Address `0.0.0.0` without secret | Red warning in the window, server not running. With 12+ characters: running, yellow hint. |
| Quit the game | Plugin: "RimWorld not reachable", trigger `disconnected`. |
| Log (`Player.log`) after everything | no red errors with "TouchDeck Bridge"; a warning "event … disabled" only drops that one event. |
