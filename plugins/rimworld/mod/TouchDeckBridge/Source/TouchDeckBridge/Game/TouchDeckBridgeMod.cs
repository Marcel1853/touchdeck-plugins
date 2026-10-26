// Einstieg des Mods: Einstellungen (Server an/aus, Adresse, Port, Geheimwort, Sendeintervall) und
// das Einstellungsfenster im Spiel. Der Server selbst wird in Bridge gestartet.
using System;
using RimWorld;
using TouchDeckBridge.Protocol;
using UnityEngine;
using Verse;

namespace TouchDeckBridge
{
    public class BridgeSettings : ModSettings
    {
        public bool enabled = true;
        public string address = ServerConfig.DefaultAddress;
        public string port = ServerConfig.DefaultPort.ToString();
        public string secret = "";
        public int intervalMs = 500;

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref enabled, "enabled", true);
            Scribe_Values.Look(ref address, "address", ServerConfig.DefaultAddress);
            Scribe_Values.Look(ref port, "port", ServerConfig.DefaultPort.ToString());
            Scribe_Values.Look(ref secret, "secret", "");
            Scribe_Values.Look(ref intervalMs, "intervalMs", 500);
        }

        public ServerConfig ToConfig() => ServerConfig.From(address, port, secret);

        /** Zustand höchstens ein- bis viermal pro Sekunde einsammeln. */
        public int IntervalClamped => Mathf.Clamp(intervalMs, 250, 5000);
    }

    public class TouchDeckBridgeMod : Mod
    {
        public static BridgeSettings Settings;
        public static string Version = "0.2.0";
        bool showSecret;

        public TouchDeckBridgeMod(ModContentPack content) : base(content)
        {
            Settings = GetSettings<BridgeSettings>();
            try
            {
                var v = content?.ModMetaData?.ModVersion;
                if (!string.IsNullOrEmpty(v)) Version = v;
            }
            catch (Exception) { /* ältere About.xml ohne modVersion */ }
        }

        public override string SettingsCategory() => "TouchDeck Bridge";

        public override void DoSettingsWindowContents(Rect inRect)
        {
            var s = Settings;
            var list = new Listing_Standard();
            list.Begin(inRect);

            list.CheckboxLabeled("TDB_Enabled".Translate(), ref s.enabled, "TDB_EnabledTip".Translate());
            list.Gap(6f);

            s.address = list.TextEntryLabeled("TDB_Address".Translate(), s.address ?? "");
            list.Label("TDB_AddressHint".Translate(), -1f);
            s.port = list.TextEntryLabeled("TDB_Port".Translate(), s.port ?? "");
            list.Gap(6f);

            var secretRect = list.GetRect(Text.LineHeight);
            var labelRect = secretRect.LeftPart(0.5f);
            var fieldRect = secretRect.RightPart(0.5f);
            Widgets.Label(labelRect, "TDB_Secret".Translate());
            var toggle = new Rect(fieldRect.xMax - 70f, fieldRect.y, 70f, fieldRect.height);
            fieldRect.width -= 74f;
            // Verdeckt nur Punkte; zum Bearbeiten „Anzeigen“ drücken
            if (showSecret) s.secret = Widgets.TextField(fieldRect, s.secret ?? "");
            else Widgets.Label(fieldRect, string.IsNullOrEmpty(s.secret) ? "TDB_SecretEmpty".Translate().ToString()
                                                                          : new string('•', Math.Min(s.secret.Length, 24)));
            if (Widgets.ButtonText(toggle, showSecret ? "TDB_Hide".Translate() : "TDB_Show".Translate())) showSecret = !showSecret;
            list.Label("TDB_SecretHint".Translate(), -1f);
            list.Gap(6f);

            list.Label("TDB_Interval".Translate(s.IntervalClamped));
            s.intervalMs = (int)list.Slider(s.IntervalClamped, 250f, 5000f);
            s.intervalMs = s.intervalMs / 50 * 50;
            list.GapLine();

            // Zustand des Servers
            var cfg = s.ToConfig();
            if (!s.enabled) list.Label("TDB_StatusOff".Translate());
            else if (Bridge.Running) list.Label("TDB_StatusRunning".Translate(Bridge.ListeningOn, Bridge.ClientCount));
            else list.Label("TDB_StatusStopped".Translate(Bridge.LastError ?? "-"));
            if (cfg.Blocked)
            {
                GUI.color = ColorLibrary.RedReadable;
                list.Label("TDB_StatusBlocked".Translate(Proto.MinRemoteSecret));
                GUI.color = Color.white;
            }
            else if (!cfg.IsLoopback)
            {
                GUI.color = ColorLibrary.Gold;
                list.Label("TDB_RemoteWarning".Translate());
                GUI.color = Color.white;
            }
            foreach (var p in cfg.Problems)
                if (!cfg.Blocked || !p.Contains("secret")) list.Label("TDB_Problem".Translate(p));
            list.Gap(6f);
            if (list.ButtonText("TDB_Apply".Translate())) Bridge.Restart();
            list.Label("TDB_ApplyHint".Translate());
            list.End();
        }

        public override void WriteSettings()
        {
            base.WriteSettings();
            // Geänderte Adresse, Port oder Geheimwort: Server startet selbst neu (kein Spielneustart nötig)
            Bridge.ApplySettings();
        }
    }
}
