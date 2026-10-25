// Sammelt den Zustand für TouchDeck ein. Nur im Hauptthread aufrufen (Bridge.Tick).
// Keine Karten-Scans: nur vorhandene Listen und Zähler (FreeColonists, resourceCounter, ColonistBar).
using System;
using System.Collections.Generic;
using RimWorld;
using Verse;

namespace TouchDeckBridge
{
    public static class GameState
    {
        public const int MaxNames = 12;

        public static bool InGame =>
            Current.ProgramState == ProgramState.Playing && Current.Game != null && Find.CurrentMap != null;

        public static Dictionary<string, object> Collect()
        {
            var st = new Dictionary<string, object> { ["inGame"] = false };
            if (!InGame) return st;
            st["inGame"] = true;
            var map = Find.CurrentMap;
            var tm = Find.TickManager;

            // Zeit
            st["tick"] = tm.TicksGame;
            st["speed"] = (int)tm.CurTimeSpeed;
            st["paused"] = tm.Paused;
            st["forcePaused"] = tm.ForcePaused;
            st["devMode"] = Prefs.DevMode;
            try
            {
                var longLat = Find.WorldGrid.LongLatOf(map.Tile);
                st["date"] = GenDate.DateFullStringAt(GenTicks.TicksAbs, longLat);
                st["hour"] = GenLocalDate.HourOfDay(map);
            }
            catch (Exception)
            {
                st["date"] = "";
                st["hour"] = 0;
            }

            // Kolonie und Karte
            st["colony"] = Faction.OfPlayerSilentFail?.Name ?? "";
            st["map"] = map.Parent?.LabelCap.ToString() ?? "";
            st["save"] = Bridge.SaveName ?? "";

            // Kolonisten der aktuellen Karte
            var colonists = map.mapPawns.FreeColonists;
            st["colonists"] = colonists.Count;
            st["prisoners"] = map.mapPawns.PrisonersOfColonyCount;
            float min = 2f, sum = 0f;
            var moodCount = 0;
            var minName = "";
            foreach (var p in colonists)
            {
                var mood = p?.needs?.mood;
                if (mood == null || p.Dead) continue;
                var v = mood.CurLevelPercentage;
                sum += v;
                moodCount++;
                if (v < min)
                {
                    min = v;
                    minName = p.LabelShort;
                }
            }
            st["moodMin"] = moodCount > 0 ? (object)Math.Round(min * 100) : null;
            st["moodAvg"] = moodCount > 0 ? (object)Math.Round(sum / moodCount * 100) : null;
            st["moodMinName"] = minName;

            // Eingezogen (nur, wer einziehbar ist)
            int draftable = 0, drafted = 0;
            foreach (var p in map.mapPawns.FreeColonistsSpawned)
            {
                if (!CanDraft(p)) continue;
                draftable++;
                if (p.drafter.Drafted) drafted++;
            }
            st["draftable"] = draftable;
            st["drafted"] = drafted;

            // Reihenfolge der Kolonistenleiste (so, wie man sie oben im Spiel sieht)
            var names = new List<object>();
            foreach (var p in ColonistsInOrder())
            {
                if (names.Count >= MaxNames) break;
                names.Add(p.LabelShort);
            }
            st["names"] = names;

            // Vorräte (Zähler des Spiels, nur Lagerzonen)
            var rc = map.resourceCounter;
            st["silver"] = rc.Silver;
            st["steel"] = rc.GetCount(ThingDefOf.Steel);
            st["components"] = rc.GetCount(ThingDefOf.ComponentIndustrial);
            st["medicine"] = rc.GetCount(ThingDefOf.MedicineHerbal) + rc.GetCount(ThingDefOf.MedicineIndustrial)
                             + rc.GetCount(ThingDefOf.MedicineUltratech);
            st["nutrition"] = Math.Round(rc.TotalHumanEdibleNutrition);

            // Wetter und Außentemperatur
            st["weather"] = map.weatherManager?.curWeather?.LabelCap.ToString() ?? "";
            var temp = map.mapTemperature.OutdoorTemp;
            st["tempC"] = Math.Round(temp, 1);
            st["temp"] = GenText.ToStringTemperature(temp, "F0");

            // Forschung
            var proj = Find.ResearchManager?.GetProject();
            st["research"] = proj?.LabelCap.ToString() ?? "";
            st["researchPct"] = proj != null ? (object)Math.Floor(proj.ProgressPercent * 100) : null;

            // Gefahr wie für die Musik des Spiels: none, low, high
            st["danger"] = map.dangerWatcher.DangerRating.ToString().ToLowerInvariant();

            // Briefe
            st["letters"] = Find.LetterStack?.LettersListForReading?.Count ?? 0;
            st["lastLetter"] = Bridge.LastLetter != null ? Patches.LetterTitle(Bridge.LastLetter) : "";
            return st;
        }

        public static bool CanDraft(Pawn p) =>
            p != null && p.Spawned && !p.Dead && !p.Downed && p.drafter != null && p.drafter.ShowDraftGizmo;

        /** Kolonisten in der Reihenfolge der Kolonistenleiste (alle Karten); Rückfall: freie Kolonisten der Karte. */
        public static List<Pawn> ColonistsInOrder()
        {
            var list = new List<Pawn>();
            try
            {
                var bar = Find.ColonistBar?.GetColonistsInOrder();
                if (bar != null)
                    foreach (var p in bar)
                        if (p != null && !p.Dead) list.Add(p);
            }
            catch (Exception) { /* Leiste noch nicht aufgebaut */ }
            if (list.Count == 0 && Find.CurrentMap != null) list.AddRange(Find.CurrentMap.mapPawns.FreeColonists);
            return list;
        }
    }
}
