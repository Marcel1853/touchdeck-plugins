# TouchDeck plugins

🇩🇪 [Deutsche Version](README.de.md)

Plugins add new **actions** and **triggers** to [TouchDeck](https://github.com/Marcel1853) –
the macro remote control for Linux. This repo contains:

| | |
|---|---|
| [`plugins.json`](plugins.json) | The list for the **marketplace** in TouchDeck (Plugins › Marketplace) |
| [`examples/`](examples/) | Example plugins to learn from and copy |
| [Wiki](../../wiki) | The guide: writing, testing and publishing plugins |

## Plugins in this repo

| Folder | Kind | What it does |
|---|---|---|
| [`plugins/clipboard-slots`](plugins/clipboard-slots) | advanced (Python) | Clipboard manager: slots, history, clipboard ↔ value, clean-ups, ready-made page (MIT) |
| [`plugins/factorio`](plugins/factorio) | advanced (Python) | Factorio live on your buttons (research, power with graphs, evolution …) and game control; needs the included mod “TouchDeck Bridge”, ready-made pages (MIT) |

Install them from the marketplace in TouchDeck. Each plugin has its own license (see its folder).

## Two kinds of plugins

- **Regular plugins** – JavaScript, sandboxed inside TouchDeck. They may only do what
  they declare in `plugin.json` (certain web addresses, values, notifications). The
  default, and enough for most ideas.
- **Advanced plugins** – own programs (Python, Node.js, …) with full rights. They only
  run if the user deliberately enables advanced mode at their own risk.

## Examples

| Folder | Kind | Shows |
|---|---|---|
| [`examples/example`](examples/example) | regular (JavaScript) | actions, trigger, timer, values, internet, settings |
| [`examples/example-python`](examples/example-python) | advanced (Python) | reading system values, running commands, trigger |
| [`examples/example-node`](examples/example-node) | advanced (Node.js) | counting, values, trigger |

To try one, copy the folder and load it in TouchDeck under **Plugins › Develop**.

## Getting your plugin into the marketplace

1. Publish the plugin as a **public** GitHub repo (`plugin.json` in the root folder),
   ideally with a release such as `v1.0.0`.
2. Open a pull request against this repo that adds an entry to `plugins.json`:

   ```json
   {
     "repo": "your-name/touchdeck-my-plugin",
     "name": { "en": "My plugin", "de": "Mein Plugin" },
     "description": { "en": "What it does", "de": "Was es macht" },
     "author": "Your name",
     "license": "MIT"
   }
   ```

   `name` and `description` can be plain text or translations like above. If the plugin
   lives in a sub-folder of a repo, add `"path": "folder/of/the/plugin"`.

Entries are reviewed before they are added. Still: TouchDeck shows the source,
license and permissions before every installation – only install what you can follow.

## Public does not mean free

Plugins have to be **public** so that everyone can read the code before installing
it. That does **not** mean anyone may copy or reuse it. Every plugin may have its own
license:

- Put a `LICENSE` file into your repo and the license name into `plugin.json`
  (`"license": "MIT"`) and into your marketplace entry.
- **Without a license, all rights stay with the author** – others may read the code,
  but not copy, change or publish it.
- If you want to allow reuse, pick an open license such as MIT, Apache-2.0 or
  GPL-3.0. If you don't, write for example `"license": "All rights reserved"`.

## License of this repo

The examples and the guide in this repo are under the [MIT license](LICENSE) – copying
and changing is explicitly welcome. Plugins listed in `plugins.json` keep their own
licenses.
