# Clipboard Slots for TouchDeck

🇩🇪 [Deutsche Version](README.de.md)

**Advanced TouchDeck plugin.** Turns buttons into a clipboard manager: save texts into slots,
bring them back with one tap, history of recent copies, clipboard to a value and back, quick text
clean-ups. It only uses TouchDeck's official plugin messages (actions, triggers, values, log) and
does not rebuild anything TouchDeck already does.

## Requirements

- TouchDeck 0.9 (Linux, X11), **advanced mode** switched on (Plugins › Advanced)
- Python 3.8 or newer (already included in Linux Mint)
- A clipboard tool: `xclip` (recommended), `xsel` or `wl-clipboard`

```
sudo apt install xclip
```

**Windows (very early alpha, untested):** Python 3.8+ from python.org is enough, no clipboard tool
is needed. The slots are stored in `%APPDATA%\touchdeck-clipboard-slots`.

## Setup

1. Plugins › Marketplace › “Clipboard Slots” › **Check** › install (confirm twice, because it is an
   advanced plugin). Without the marketplace you can also enter
   `Marcel1853/touchdeck-plugins/plugins/clipboard-slots`.
2. **Import the ready-made page:** on the plugin card (or under “Ready-made pages” in the page list),
   click “📄 Zwischenablage Seite import”. You get a page with 12 slot buttons and 6 tool buttons – no need
   to create buttons one by one.
3. Done. There are no required settings; the defaults fit everyday use.

### Using the page

- **Tap a slot button:** puts the slot into the clipboard and pastes it. Pasting lives in the
  template “Einfügen” (`Ctrl+V`). For terminals, change it once to `Ctrl+Shift+V` there; all buttons
  follow.
- **Hold a slot button (about 0.5 s):** saves the current clipboard content into this slot.
- The label shows a preview of the slot (`{Slot1}` …).
- Tool row: paste the second-to-last copy, the one before, paste as a single line, paste a link
  without tracking, clear the history, auto-save on/off.

### Auto-save (ring buffer)

With the “Auto-save” button **every new copy (`Ctrl+C`) automatically goes into the next slot**:
slot 1, 2, 3 … and after the last one back to 1.

- Texts that are already in a slot are not saved twice.
- The mode survives a restart. `{AutoSave}` shows on/off, `{NextSlot}` the next slot.
- Auto-save overwrites slots. To keep fixed slots, set “Auto-save uses slots 1 to …” in the
  settings, e.g. to 10, and use the remaining ones by hand.
- “Clear all slots” resets the counter to 1.
- More or fewer slots: `python3 tools/make_profile.py 20` creates a new page file; set the number
  in the plugin settings to match. Slot fields also accept placeholders like `{Eingabe.Nummer}`.

## Actions

| Action | What it does |
| --- | --- |
| Save clipboard to slot | Copies the current text into slot 1–50 |
| Put slot into clipboard | Brings the text from the slot back |
| Put history entry into clipboard | 1 = last copied, 2 = the one before, … |
| Clipboard to value | Writes the text into a TouchDeck value |
| Value to clipboard | Copies a TouchDeck value (e.g. from an HTTP response) |
| Clean up clipboard text | Trim, single line, UPPER, lower, strip tracking from a link |
| Auto-save into slots | Every new copy into the next slot (ring buffer), on/off/toggle |
| Clear | History, clipboard, one slot or all slots |

**Your own buttons:** the ready-made page already does this. If you build your own: action “Put slot
into clipboard”, followed by TouchDeck's regular action “Keyboard shortcut” with `Ctrl+V` (in a
terminal `Ctrl+Shift+V`). The slot is then guaranteed to be in the clipboard when the shortcut fires.

## Trigger

- **Clipboard text changed**: the event provides `{Event.Text}` and `{Event.Length}`. Changes made
  by the plugin itself do not fire it.

## Values for live displays

| Value | Content |
| --- | --- |
| `Clip` | Preview of the clipboard (one line, 60 characters) |
| `ClipLength` | Length in characters |
| `ClipCount` | Entries in the history |
| `Slot1` … `SlotN` | Preview of the slot (40 characters), empty if empty |
| `AutoSave` / `NextSlot` | Auto-save “on” or “off” / next slot |

Show them in button labels with `{Slot1}`, or as the live display “Value of a variable”.

## Settings

All optional: number of slots (12), keep slots after restart (on), record history (on),
history length (20), ignore texts longer than … characters (10000), check interval (1000 ms).

## Privacy – what is stored

- **History:** in memory only, never written to disk, and gone when the plugin stops. If you copy
  passwords, switch the history off in the settings or clear it with an action.
- **Slots:** only if “Keep slots after restart” is on, in
  `~/.config/touchdeck-clipboard-slots/slots.json` (mode 600, only you; the auto-save mode is stored
  there too). Do not keep anything there that must stay secret, or switch the setting off.
- The plugin sends nothing over the network and downloads no code.

## Limits

- Values in TouchDeck are limited to 1000 characters: “Clipboard to value” shortens longer texts.
- Text only. Images and files in the clipboard are ignored.
- The clipboard is polled (every second by default), not watched by events.

License: MIT
