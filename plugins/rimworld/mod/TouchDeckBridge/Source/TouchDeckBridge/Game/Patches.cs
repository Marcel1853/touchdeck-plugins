// Harmony-Patches für Ereignisse. Nur Methoden, die selten laufen (Brief kommt, Pawn stirbt, Nervenzusammenbruch,
// Forschung fertig, Speichern/Laden) – nichts pro Tick. Jeder Patch wird einzeln angelegt: Fehlt eine Methode
// in einer anderen Spielversion, fällt nur dieses Ereignis weg (Meldung im Log), der Rest läuft weiter.
using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using RimWorld;
using Verse;
using Verse.AI;

namespace TouchDeckBridge
{
    public static class Patches
    {
        public const int MaxText = 300;

        public static void Apply(Harmony harmony)
        {
            Patch(harmony, "letter", AccessTools.Method(typeof(LetterStack), nameof(LetterStack.ReceiveLetter),
                      new[] { typeof(Letter), typeof(string), typeof(int), typeof(bool) }), null, nameof(LetterPostfix));
            Patch(harmony, "colonist_died", AccessTools.Method(typeof(Pawn), nameof(Pawn.Kill)), nameof(KillPrefix), nameof(KillPostfix));
            Patch(harmony, "mental_break", AccessTools.Method(typeof(MentalStateHandler), nameof(MentalStateHandler.TryStartMentalState)),
                  null, nameof(MentalPostfix));
            Patch(harmony, "research_finished", AccessTools.Method(typeof(ResearchManager), nameof(ResearchManager.FinishProject)),
                  null, nameof(ResearchPostfix));
            Patch(harmony, "save name", AccessTools.Method(typeof(GameDataSaveLoader), nameof(GameDataSaveLoader.SaveGame),
                      new[] { typeof(string) }), null, nameof(SavePostfix));
            Patch(harmony, "load name", AccessTools.Method(typeof(GameDataSaveLoader), nameof(GameDataSaveLoader.LoadGame),
                      new[] { typeof(string) }), nameof(LoadPrefix), null);
        }

        static void Patch(Harmony harmony, string what, MethodInfo target, string prefix, string postfix)
        {
            try
            {
                if (target == null) throw new MissingMethodException("target method not found");
                harmony.Patch(target,
                              prefix == null ? null : new HarmonyMethod(typeof(Patches), prefix),
                              postfix == null ? null : new HarmonyMethod(typeof(Patches), postfix));
            }
            catch (Exception e)
            {
                Log.Warning("[TouchDeck Bridge] event '" + what + "' disabled, patch failed: " + e.Message);
            }
        }

        static string Clip(string s)
        {
            s = (s ?? "").StripTags().Replace("\r", "").Trim();
            return s.Length > MaxText ? s.Substring(0, MaxText - 1) + "…" : s;
        }

        public static string LetterTitle(Letter letter)
        {
            try
            {
                return Clip(letter.Label.ToString());
            }
            catch (Exception)
            {
                return "";
            }
        }

        // ---------------- Briefe ----------------

        /** big (Überfall, Belagerung …), small oder "". */
        public static string Threat(Letter letter) =>
            letter.def == LetterDefOf.ThreatBig ? "big" : letter.def == LetterDefOf.ThreatSmall ? "small" : "";

        // Verzögerte Briefe laufen später ein zweites Mal hier durch (dann mit delayTicks 0); gemeldet wird nur,
        // was wirklich im Stapel angekommen ist.
        static void LetterPostfix(LetterStack __instance, Letter let, int delayTicks)
        {
            try
            {
                if (let == null || delayTicks > 0 || !__instance.LettersListForReading.Contains(let)) return;
                Bridge.LastLetter = let;
                var threat = Threat(let);
                var text = let is ChoiceLetter choice ? Clip(choice.Text.ToString()) : "";
                var title = LetterTitle(let);
                Bridge.Emit("letter", new Dictionary<string, object>
                {
                    ["title"] = title, ["kind"] = let.def?.defName ?? "", ["text"] = text, ["threat"] = threat,
                }, "letter|" + let.ID);
            }
            catch (Exception e)
            {
                Log.ErrorOnce("[TouchDeck Bridge] letter event: " + e, 0x7d0b1e1);
            }
        }

        // ---------------- Tod eines Kolonisten ----------------

        static void KillPrefix(Pawn __instance, out bool __state)
        {
            __state = false;
            try
            {
                __state = __instance != null && !__instance.Dead && __instance.IsColonist;
            }
            catch (Exception) { }
        }

        static void KillPostfix(Pawn __instance, bool __state)
        {
            try
            {
                if (!__state || !__instance.Dead) return;
                Bridge.Emit("colonist_died", new Dictionary<string, object> { ["name"] = __instance.LabelShort },
                            "died|" + __instance.thingIDNumber);
            }
            catch (Exception e)
            {
                Log.ErrorOnce("[TouchDeck Bridge] death event: " + e, 0x7d0b1e2);
            }
        }

        // ---------------- Nervenzusammenbruch ----------------

        static void MentalPostfix(bool __result, MentalStateDef stateDef, Pawn ___pawn)
        {
            try
            {
                if (!__result || ___pawn == null || !___pawn.IsColonist || stateDef == null) return;
                Bridge.Emit("mental_break", new Dictionary<string, object>
                {
                    ["name"] = ___pawn.LabelShort, ["kind"] = stateDef.LabelCap.ToString(), ["defName"] = stateDef.defName,
                }, "mental|" + ___pawn.thingIDNumber + "|" + stateDef.defName);
            }
            catch (Exception e)
            {
                Log.ErrorOnce("[TouchDeck Bridge] mental break event: " + e, 0x7d0b1e3);
            }
        }

        // ---------------- Forschung ----------------

        static void ResearchPostfix(ResearchProjectDef proj)
        {
            try
            {
                if (proj == null || !proj.IsFinished) return;
                Bridge.Emit("research_finished", new Dictionary<string, object>
                {
                    ["name"] = proj.LabelCap.ToString(), ["defName"] = proj.defName,
                }, "research|" + proj.defName);
            }
            catch (Exception e)
            {
                Log.ErrorOnce("[TouchDeck Bridge] research event: " + e, 0x7d0b1e4);
            }
        }

        // ---------------- Spielstand-Name ----------------

        static void SavePostfix(string fileName)
        {
            if (!string.IsNullOrEmpty(fileName)) Bridge.SaveName = fileName;
        }

        static void LoadPrefix(string saveFileName)
        {
            if (!string.IsNullOrEmpty(saveFileName)) Bridge.SaveName = saveFileName;
            Bridge.LastLetter = null;
        }
    }
}
