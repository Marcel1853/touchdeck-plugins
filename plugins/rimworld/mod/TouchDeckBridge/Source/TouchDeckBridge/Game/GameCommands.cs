// Befehle vom Plugin, ausgeführt im Hauptthread (Bridge.Tick). Jeder Befehl antwortet genau einmal
// mit einem Code; das Plugin macht daraus einen Text auf Deutsch oder Englisch.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using HarmonyLib;
using RimWorld;
using RimWorld.Planet;
using TouchDeckBridge.Protocol;
using Verse;
using Command = TouchDeckBridge.Protocol.Command;

namespace TouchDeckBridge
{
    public static class GameCommands
    {
        public const string QuickSaveName = "TouchDeck-Quicksave";

        static Dictionary<string, object> A(string key, object value) => new Dictionary<string, object> { [key] = value };

        public static void Run(Command cmd)
        {
            var a = cmd.Args;
            if (cmd.Name == "state")
            {
                Bridge.RequestState();
                cmd.Reply(true, "state");
                return;
            }
            if (!GameState.InGame)
            {
                cmd.Reply(false, "no_game", null, "No game loaded");
                return;
            }
            switch (cmd.Name)
            {
                case "pause": Pause(cmd, Json.Str(a, "op", "toggle")); return;
                case "speed": Speed(cmd, Json.Str(a, "op", "set"), (int)Json.Num(a, "value", 1)); return;
                case "save": Save(cmd, Json.Str(a, "name").Trim()); return;
                case "screenshot": Screenshot(cmd); return;
                case "draft": Draft(cmd, Json.Str(a, "op", "toggle")); return;
                case "jump": Jump(cmd, (int)Json.Num(a, "n", 1)); return;
                case "cycle": Cycle(cmd, Json.Num(a, "dir", 1) < 0 ? -1 : 1); return;
                case "letter": Letter(cmd, Json.Str(a, "op", "jump"), (int)Json.Num(a, "id", 0)); return;
                case "message": Message(cmd, Json.Str(a, "text"), Json.Str(a, "kind", "neutral")); return;
                case "tab": Tab(cmd, Json.Str(a, "name")); return;
                case "research": Research(cmd, Json.Str(a, "name").Trim()); return;
                default:
                    cmd.Reply(false, "unknown_command", A("value", cmd.Name));
                    return;
            }
        }

        // ---------------- Zeit ----------------

        // TickManager.PlayerCanControl ist privat (dieselbe Prüfung macht TogglePaused); fehlt sie, gilt „erlaubt“
        static readonly MethodInfo CanControlGetter = AccessTools.PropertyGetter(typeof(TickManager), "PlayerCanControl");

        /** Darf der Spieler das Tempo gerade ändern? Sonst mit dem Grund des Spiels antworten. */
        static bool CanControl(Command cmd)
        {
            if (CanControlGetter == null) return true;
            AcceptanceReport report;
            try
            {
                report = (AcceptanceReport)CanControlGetter.Invoke(Find.TickManager, null);
            }
            catch (Exception)
            {
                return true;
            }
            if (report.Accepted) return true;
            cmd.Reply(false, "no_control", A("value", report.Reason ?? ""));
            return false;
        }

        static void Pause(Command cmd, string op)
        {
            var tm = Find.TickManager;
            if (!CanControl(cmd)) return;
            // Pause des Spielers = Tempo „Paused“. tm.Paused ist auch wahr, wenn nur ein Fenster anhält (ForcePaused).
            var userPaused = tm.CurTimeSpeed == TimeSpeed.Paused;
            var pause = op == "on" || (op == "toggle" && !userPaused);
            if (pause != userPaused) tm.TogglePaused();
            Bridge.RequestState();
            if (!pause && tm.ForcePaused) cmd.Reply(true, "force_paused");
            else cmd.Reply(true, pause ? "paused" : "resumed");
        }

        static int MaxSpeed => Prefs.DevMode ? 4 : 3;

        static void Speed(Command cmd, string op, int value)
        {
            var tm = Find.TickManager;
            if (!CanControl(cmd)) return;
            var cur = tm.CurTimeSpeed == TimeSpeed.Paused ? (int)tm.prePauseTimeSpeed : (int)tm.CurTimeSpeed;
            if (cur < 1) cur = 1;
            int target;
            if (op == "up") target = Math.Min(cur + 1, MaxSpeed);
            else if (op == "down") target = Math.Max(cur - 1, 1);
            else target = value;
            if (target == 4 && !Prefs.DevMode)
            {
                cmd.Reply(false, "speed4_dev");
                return;
            }
            if (target < 1 || target > 4)
            {
                cmd.Reply(false, "bad_value", A("value", value));
                return;
            }
            // Wie ein Klick auf die Tempo-Knöpfe im Spiel: setzt das Tempo und hebt die Pause auf
            tm.CurTimeSpeed = (TimeSpeed)target;
            Bridge.RequestState();
            cmd.Reply(true, tm.ForcePaused ? "speed_force_paused" : "speed", A("value", target));
        }

        // ---------------- Spiel ----------------

        static void Save(Command cmd, string name)
        {
            if (GameDataSaveLoader.SavingIsTemporarilyDisabled)
            {
                cmd.Reply(false, "save_disabled");
                return;
            }
            var info = Find.GameInfo;
            if (info != null && info.permadeathMode)
                name = info.permadeathModeUniqueName;   // Permadeath erlaubt nur den eigenen Spielstand
            else if (name.Length == 0)
                name = QuickSaveName;
            name = GenFile.SanitizedFileName(name);
            if (string.IsNullOrEmpty(name))
            {
                cmd.Reply(false, "bad_value", A("value", ""));
                return;
            }
            var saveName = name;
            // Wie der Speichern-Dialog des Spiels: als „lange Aktion“ mit Ladebildschirm; Antwort, wenn fertig
            LongEventHandler.QueueLongEvent(
                () => GameDataSaveLoader.SaveGame(saveName),
                "SavingLongEvent", false,
                e =>
                {
                    Log.Warning("[TouchDeck Bridge] save failed: " + e);
                    cmd.Reply(false, "save_failed", A("value", e.Message));
                },
                true, false,
                () => cmd.Reply(true, "saved", A("name", saveName)));
        }

        static void Screenshot(Command cmd)
        {
            var file = "TouchDeck_" + DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss");
            ScreenshotTaker.TakeNonSteamShot(file);
            // Unity schreibt die Datei erst am Ende des Bildes; der Pfad steht aber schon fest
            var path = Path.Combine(GenFilePaths.ScreenshotFolderPath, file + ".png");
            cmd.Reply(true, "screenshot", A("path", path));
        }

        // ---------------- Kolonisten ----------------

        static void Draft(Command cmd, string op)
        {
            var pawns = new List<Pawn>();
            foreach (var p in Find.CurrentMap.mapPawns.FreeColonistsSpawned)
                if (GameState.CanDraft(p)) pawns.Add(p);
            if (pawns.Count == 0)
            {
                cmd.Reply(false, "no_colonists");
                return;
            }
            bool draft;
            if (op == "on") draft = true;
            else if (op == "off") draft = false;
            else draft = pawns.Exists(p => !p.drafter.Drafted);   // umschalten: sind nicht alle drin, alle einziehen
            foreach (var p in pawns)
                if (p.drafter.Drafted != draft) p.drafter.Drafted = draft;
            Bridge.RequestState();
            cmd.Reply(true, draft ? "drafted" : "undrafted", A("count", pawns.Count));
        }

        static void Jump(Command cmd, int n)
        {
            var list = GameState.ColonistsInOrder();
            if (n < 1 || n > list.Count)
            {
                cmd.Reply(false, "no_colonist", new Dictionary<string, object> { ["value"] = n, ["count"] = list.Count });
                return;
            }
            JumpTo(cmd, list[n - 1]);
        }

        static void Cycle(Command cmd, int dir)
        {
            var list = GameState.ColonistsInOrder();
            if (list.Count == 0)
            {
                cmd.Reply(false, "no_colonists");
                return;
            }
            var selected = Find.Selector?.SelectedPawns;
            var index = -1;
            if (selected != null && selected.Count > 0) index = list.IndexOf(selected[0]);
            index = index < 0 ? (dir > 0 ? 0 : list.Count - 1) : (index + dir + list.Count) % list.Count;
            JumpTo(cmd, list[index]);
        }

        static void JumpTo(Command cmd, Pawn p)
        {
            CameraJumper.TryJumpAndSelect(p);
            cmd.Reply(true, "jumped", A("name", p.LabelShort));
        }

        // ---------------- Meldungen ----------------

        /** id 0 = letzter Brief; sonst ein Brief aus dem Verlauf (auch schon weggeklickt). */
        static void Letter(Command cmd, string op, int id)
        {
            Letter letter;
            var stack = Find.LetterStack?.LettersListForReading;
            if (id > 0)
            {
                letter = GameState.FindLetter(id);
                if (letter == null)
                {
                    cmd.Reply(false, "letter_gone");
                    return;
                }
            }
            else
            {
                letter = Bridge.LastLetter;
                if (letter == null || stack == null || !stack.Contains(letter))
                {
                    // gemerkter Brief schon weg: den neuesten im Stapel nehmen
                    letter = stack != null && stack.Count > 0 ? stack[stack.Count - 1] : null;
                }
            }
            if (letter == null)
            {
                cmd.Reply(false, "no_letter");
                return;
            }
            var title = Patches.LetterTitle(letter);
            if (op == "open")
            {
                // Im Stapel wie ein Klick auf den Brief, sonst wie im Verlauf-Fenster
                if (stack != null && stack.Contains(letter)) letter.OpenLetter();
                else ((IArchivable)letter).OpenArchived();
                cmd.Reply(true, "letter_opened", A("name", title));
                return;
            }
            var target = letter.lookTargets != null ? letter.lookTargets.PrimaryTarget : GlobalTargetInfo.Invalid;
            if (!target.IsValid || !CameraJumper.CanJump(target))
            {
                cmd.Reply(false, "no_target", A("name", title));
                return;
            }
            CameraJumper.TryJumpAndSelect(target);
            cmd.Reply(true, "letter_jumped", A("name", title));
        }

        static void Message(Command cmd, string text, string kind)
        {
            text = (text ?? "").Trim();
            if (text.Length == 0)
            {
                cmd.Reply(false, "empty_text");
                return;
            }
            if (text.Length > 500) text = text.Substring(0, 500);
            MessageTypeDef def;
            switch (kind)
            {
                case "positive": def = MessageTypeDefOf.PositiveEvent; break;
                case "negative": def = MessageTypeDefOf.NegativeEvent; break;
                case "threat": def = MessageTypeDefOf.ThreatSmall; break;
                default: def = MessageTypeDefOf.NeutralEvent; break;
            }
            Messages.Message(text, def, false);
            cmd.Reply(true, "message_shown");
        }

        // ---------------- Fenster und Forschung ----------------

        static void Tab(Command cmd, string name)
        {
            var def = string.IsNullOrEmpty(name) ? null : DefDatabase<MainButtonDef>.GetNamedSilentFail(name);
            if (def == null || def.tabWindowClass == null)
            {
                cmd.Reply(false, "no_tab", A("value", name));
                return;
            }
            var wasOpen = Find.MainTabsRoot.OpenTab == def;
            Find.MainTabsRoot.ToggleTab(def);
            cmd.Reply(true, wasOpen ? "tab_closed" : "tab_opened", A("name", def.LabelCap.ToString()));
        }

        static void Research(Command cmd, string name)
        {
            if (name.Length == 0)
            {
                cmd.Reply(false, "bad_value", A("value", ""));
                return;
            }
            // Erst exakt (interner Name oder Anzeigename), dann eindeutiger Teiltreffer im Anzeigenamen
            ResearchProjectDef found = null;
            var partial = new List<ResearchProjectDef>();
            foreach (var d in DefDatabase<ResearchProjectDef>.AllDefsListForReading)
            {
                var label = d.LabelCap.ToString();
                if (string.Equals(d.defName, name, StringComparison.OrdinalIgnoreCase) || string.Equals(label, name, StringComparison.OrdinalIgnoreCase))
                {
                    found = d;
                    break;
                }
                if (label.IndexOf(name, StringComparison.OrdinalIgnoreCase) >= 0) partial.Add(d);
            }
            if (found == null && partial.Count == 1) found = partial[0];
            if (found == null)
            {
                var names = new List<string>();
                foreach (var d in partial)
                    if (names.Count < 5) names.Add(d.LabelCap.ToString());
                cmd.Reply(false, partial.Count > 1 ? "research_ambiguous" : "research_unknown",
                          new Dictionary<string, object> { ["value"] = name, ["list"] = string.Join(", ", names) });
                return;
            }
            var label2 = found.LabelCap.ToString();
            if (found.IsFinished)
            {
                cmd.Reply(false, "research_done", A("name", label2));
                return;
            }
            if (!found.CanStartNow)
            {
                cmd.Reply(false, "research_locked", A("name", label2));
                return;
            }
            Find.ResearchManager.SetCurrentProject(found);
            Bridge.RequestState();
            cmd.Reply(true, "research_set", A("name", label2));
        }
    }
}
