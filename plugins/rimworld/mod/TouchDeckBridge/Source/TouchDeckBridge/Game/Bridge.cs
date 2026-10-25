// Verbindet Server und Spiel. Ein unsichtbares Unity-Objekt (BridgeRunner) läuft in jedem Bild im
// Hauptthread – im Hauptmenü, im Spiel und bei Pause. Nur dort werden Befehle ausgeführt und der Zustand
// eingesammelt. Der Netzwerk-Thread bekommt fertige Textzeilen und fasst das Spiel nie an.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using HarmonyLib;
using RimWorld;
using TouchDeckBridge.Protocol;
using UnityEngine;
using Verse;
using Command = TouchDeckBridge.Protocol.Command;

namespace TouchDeckBridge
{
    [StaticConstructorOnStartup]
    public static class Bridge
    {
        public const string HarmonyId = "Marcel171297.TouchDeckBridge";
        static readonly CommandQueue Queue = new CommandQueue();
        static readonly Deduper Dedup = new Deduper(4000);
        static readonly Stopwatch Clock = Stopwatch.StartNew();
        static BridgeServer server;
        static long nextStateMs;
        static bool forceState;

        public static string LastError;
        public static bool Running => server != null && server.Running;
        public static int ClientCount => server?.ClientCount ?? 0;
        public static string ListeningOn => server == null ? "-" : server.Config.AddressText + ":" + server.BoundPort;

        /** Spielstand-Name: zuletzt gespeichert oder geladen (von Patches gesetzt). */
        public static string SaveName = "";
        /** Zuletzt angekommener Brief (für „Kamera zum letzten Brief“). */
        public static Letter LastLetter;

        static Bridge()
        {
            try
            {
                var go = new GameObject("TouchDeckBridge");
                UnityEngine.Object.DontDestroyOnLoad(go);
                go.AddComponent<BridgeRunner>();
            }
            catch (Exception e)
            {
                Log.Error("[TouchDeck Bridge] could not create runner: " + e);
            }
            Patches.Apply(new Harmony(HarmonyId));
            ApplySettings();
        }

        static void LogMsg(string msg) => Log.Message("[TouchDeck Bridge] " + msg);

        /** Nur neu starten, wenn sich etwas geändert hat. */
        public static void ApplySettings()
        {
            var s = TouchDeckBridgeMod.Settings;
            if (s == null) return;
            var cfg = s.ToConfig();
            if (s.enabled && server != null && server.Running && server.Config.SameAs(cfg)) return;
            if (!s.enabled && server == null) return;
            Restart();
        }

        public static void Restart()
        {
            try
            {
                server?.Stop();
            }
            catch (Exception e)
            {
                Log.Warning("[TouchDeck Bridge] stop failed: " + e.Message);
            }
            server = null;
            LastError = null;
            var s = TouchDeckBridgeMod.Settings;
            if (s == null || !s.enabled)
            {
                LogMsg("server off (settings)");
                return;
            }
            var cfg = s.ToConfig();
            foreach (var p in cfg.Problems) Log.Warning("[TouchDeck Bridge] " + p);
            if (cfg.Blocked)
            {
                LastError = "secret required";
                return;
            }
            try
            {
                server = new BridgeServer(cfg, Queue, LogMsg, TouchDeckBridgeMod.Version, VersionControl.CurrentVersionStringWithRev);
                server.Start();
                forceState = true;
            }
            catch (Exception e)
            {
                LastError = e.Message;
                server = null;
                Log.Warning("[TouchDeck Bridge] could not start server on " + cfg.AddressText + ":" + cfg.Port + ": " + e.Message);
            }
        }

        /** Ereignis an alle Clients (aus Patches, also Hauptthread). Gleiche Meldungen innerhalb von 4 s fallen weg. */
        public static void Emit(string name, Dictionary<string, object> data, string dedupKey = null)
        {
            try
            {
                if (server == null || server.ClientCount == 0) return;
                if (!Dedup.Allow(name + "|" + (dedupKey ?? Json.Serialize(data)), Clock.ElapsedMilliseconds)) return;
                server.Broadcast(Proto.Event(name, data));
                forceState = true;   // Zustand gleich mitschicken (z. B. neue Stimmung, weniger Kolonisten)
            }
            catch (Exception e)
            {
                Log.Warning("[TouchDeck Bridge] event " + name + " failed: " + e.Message);
            }
        }

        public static void RequestState() => forceState = true;

        /** Spiel wird beendet: Port freigeben. */
        public static void Shutdown()
        {
            server?.Stop();
            server = null;
        }

        /** Einmal pro Bild aus BridgeRunner.Update (Hauptthread). */
        internal static void Tick()
        {
            if (server == null) return;
            // Befehle: höchstens 8 pro Bild, damit nichts ruckelt
            for (var i = 0; i < 8 && Queue.TryTake(out var cmd); i++)
            {
                try
                {
                    GameCommands.Run(cmd);
                }
                catch (Exception e)
                {
                    Log.Warning("[TouchDeck Bridge] command " + cmd.Name + " failed: " + e);
                    cmd.Reply(false, "error", new Dictionary<string, object> { ["value"] = e.Message });
                }
            }
            var now = Clock.ElapsedMilliseconds;
            if (!forceState && now < nextStateMs) return;
            if (server.ClientCount == 0 && !forceState)
            {
                nextStateMs = now + 1000;
                return;
            }
            forceState = false;
            nextStateMs = now + TouchDeckBridgeMod.Settings.IntervalClamped;
            try
            {
                server.PublishState(Proto.State(GameState.Collect()));
            }
            catch (Exception e)
            {
                Log.ErrorOnce("[TouchDeck Bridge] collecting state failed: " + e, 0x7d0b1d6);
            }
        }
    }

    /** Unsichtbares Unity-Objekt: Update läuft in jedem Bild im Hauptthread, auch im Hauptmenü und bei Pause. */
    public class BridgeRunner : MonoBehaviour
    {
        void Update()
        {
            try
            {
                Bridge.Tick();
            }
            catch (Exception e)
            {
                Log.ErrorOnce("[TouchDeck Bridge] " + e, 0x7d0b1d5);
            }
        }

        void OnApplicationQuit()
        {
            try { Bridge.Shutdown(); } catch (Exception) { }
        }
    }
}
