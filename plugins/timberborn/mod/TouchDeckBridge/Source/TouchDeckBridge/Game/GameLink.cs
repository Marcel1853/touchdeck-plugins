// Brücke zum geladenen Spielstand. Bindito legt GameLink beim Laden eines Spielstands an (Kontext „Game“) und
// gibt ihm alle Dienste per Konstruktor. Alles hier läuft im Hauptthread: Ereignisse vom EventBus des Spiels,
// Collect() und Run() aus Bridge.Tick.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Text.RegularExpressions;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.Beavers;
using Timberborn.Characters;
using Timberborn.EntitySystem;
using Timberborn.GameCycleSystem;
using Timberborn.GameFactionSystem;
using Timberborn.GameOver;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.GoodsSampling;
using Timberborn.HazardousWeatherSystem;
using Timberborn.HazardousWeatherSystemUI;
using Timberborn.Localization;
using Timberborn.NotificationSystem;
using Timberborn.Population;
using Timberborn.QuickNotificationSystem;
using Timberborn.ResourceCountingSystem;
using Timberborn.ScienceSystem;
using Timberborn.SelectionSystem;
using Timberborn.SettlementNameSystem;
using Timberborn.SingletonSystem;
using Timberborn.StatusSystem;
using Timberborn.TimeSystem;
using Timberborn.WeatherSystem;
using Timberborn.Wellbeing;
using TouchDeckBridge.Protocol;

namespace TouchDeckBridge
{
    [Context("Game")]
    public class BridgeConfigurator : Configurator
    {
        protected override void Configure()
        {
            Bind<GameLink>().AsSingleton();
        }
    }

    public class GameLink : ILoadableSingleton, IUnloadableSingleton
    {
        public const int HistorySize = 8;
        public const int AlertSlots = 8;
        /** Wie im Spiel (HazardousWeatherUISpec.ApproachingNotificationDays): erst so viele Tage vorher verrät es die Art. */
        public const float RevealDays = 3f;
        static readonly float[] Speeds = { 1f, 3f, 7f };
        static readonly Regex Tags = new Regex("<[^>]+>");
        static readonly FieldInfo VisibleStatusesField =
            typeof(StatusAggregator).GetField("_visibleStatuses", BindingFlags.NonPublic | BindingFlags.Instance);

        readonly EventBus eventBus;
        readonly SpeedManager speedManager;
        readonly IDayNightCycle dayNight;
        readonly GameCycleService cycles;
        readonly WeatherService weather;
        readonly HazardousWeatherService hazards;
        readonly PopulationService population;
        readonly WellbeingService wellbeing;
        readonly ScienceService science;
        readonly IGoodService goods;
        readonly ResourceCountingService resources;
        readonly GlobalGoodSamplingRegistry samples;
        readonly NotificationBus notificationBus;
        readonly NotificationSaver notificationSaver;
        readonly QuickNotificationService quickNotifications;
        readonly StatusAggregator statuses;
        readonly EntityRegistry entities;
        readonly EntitySelectionService selection;
        readonly GameSaver gameSaver;
        readonly SettlementReferenceService settlement;
        readonly FactionService faction;
        readonly ILoc loc;

        /** Nachrichtenverlauf, neueste zuerst (wie das Benachrichtigungsfenster des Spiels). */
        readonly List<Notification> history = new List<Notification>();
        /** Pro Warnung: welches betroffene Objekt beim nächsten Tippen dran ist. */
        readonly Dictionary<string, int> alertCursor = new Dictionary<string, int>();
        float speedBeforePause = 1f;
        int lastPopulation = -1;

        public GameLink(EventBus eventBus, SpeedManager speedManager, IDayNightCycle dayNight, GameCycleService cycles,
                        WeatherService weather, HazardousWeatherService hazards, PopulationService population,
                        WellbeingService wellbeing, ScienceService science, IGoodService goods,
                        ResourceCountingService resources, GlobalGoodSamplingRegistry samples,
                        NotificationBus notificationBus, NotificationSaver notificationSaver,
                        QuickNotificationService quickNotifications, StatusAggregator statuses, EntityRegistry entities,
                        EntitySelectionService selection, GameSaver gameSaver, SettlementReferenceService settlement,
                        FactionService faction, ILoc loc)
        {
            this.eventBus = eventBus;
            this.speedManager = speedManager;
            this.dayNight = dayNight;
            this.cycles = cycles;
            this.weather = weather;
            this.hazards = hazards;
            this.population = population;
            this.wellbeing = wellbeing;
            this.science = science;
            this.goods = goods;
            this.resources = resources;
            this.samples = samples;
            this.notificationBus = notificationBus;
            this.notificationSaver = notificationSaver;
            this.quickNotifications = quickNotifications;
            this.statuses = statuses;
            this.entities = entities;
            this.selection = selection;
            this.gameSaver = gameSaver;
            this.settlement = settlement;
            this.faction = faction;
            this.loc = loc;
        }

        public void Load()
        {
            try
            {
                // Gespeicherter Verlauf aus dem Spielstand (älteste zuerst) → neueste zuerst
                foreach (var n in notificationSaver.Notifications) history.Insert(0, n);
                if (history.Count > HistorySize) history.RemoveRange(HistorySize, history.Count - HistorySize);
            }
            catch (Exception e)
            {
                Bridge.Warn("reading saved notifications failed: " + e.Message);
            }
            notificationBus.NotificationPosted += OnNotificationPosted;
            eventBus.Register(this);
            Bridge.Game = this;
            Bridge.RequestState();
            Bridge.Log("game loaded");
        }

        public void Unload()
        {
            if (Bridge.Game == this) Bridge.Game = null;
            try
            {
                notificationBus.NotificationPosted -= OnNotificationPosted;
                eventBus.Unregister(this);
            }
            catch (Exception) { /* Szene wird ohnehin abgebaut */ }
            Bridge.RequestState();
        }

        // ---------------- Ereignisse aus dem Spiel ----------------

        void OnNotificationPosted(object sender, NotificationEventArgs e)
        {
            var n = e.Notification;
            history.Insert(0, n);
            if (history.Count > HistorySize) history.RemoveAt(history.Count - 1);
            Bridge.Emit("notification", new Dictionary<string, object>
            {
                ["text"] = Clean(n.Description), ["cycle"] = n.Cycle, ["day"] = n.CycleDay,
            });
        }

        [OnEvent]
        public void OnHazardStarted(HazardousWeatherStartedEvent e) =>
            Bridge.Emit("hazard_started", HazardData(e.HazardousWeather, weather.HazardousWeatherDuration));

        [OnEvent]
        public void OnHazardEnded(HazardousWeatherEndedEvent e) => Bridge.Emit("hazard_ended", HazardData(e.HazardousWeather, 0));

        [OnEvent]
        public void OnHazardApproaching(HazardousWeatherApproachingEvent e) =>
            Bridge.Emit("hazard_approaching", HazardData(hazards.CurrentCycleHazardousWeather, weather.HazardousWeatherDuration));

        [OnEvent]
        public void OnCycleStarted(CycleStartedEvent e) => Bridge.Emit("cycle_started", new Dictionary<string, object> { ["cycle"] = e.Cycle });

        [OnEvent]
        public void OnBeaverBorn(BeaverBornEvent e) => Bridge.Emit("beaver_born", new Dictionary<string, object>(), "born" + cycles.Cycle + "." + cycles.CycleDay + "." + Population());

        [OnEvent]
        public void OnCharacterKilled(CharacterKilledEvent e)
        {
            var c = e.Character;
            Bridge.Emit("character_died", new Dictionary<string, object>
            {
                ["name"] = c != null ? c.FirstName ?? "" : "", ["age"] = c != null ? c.Age : 0,
            });
        }

        [OnEvent]
        public void OnStatusAlertAdded(StatusAlertAddedEvent e) =>
            Bridge.Emit("alert", new Dictionary<string, object> { ["text"] = Clean(e.StatusAlert) });

        [OnEvent]
        public void OnGameOver(GameOverEvent e) => Bridge.Emit("game_over", new Dictionary<string, object>());

        [OnEvent]
        public void OnPopulationChanged(PopulationChangedEvent e)
        {
            var now = Population();
            if (lastPopulation >= 0 && now != lastPopulation) Bridge.RequestState();
            lastPopulation = now;
        }

        Dictionary<string, object> HazardData(IHazardousWeather w, int days) => new Dictionary<string, object>
        {
            ["kind"] = HazardKind(w), ["name"] = HazardName(HazardKind(w)), ["days"] = days, ["cycle"] = cycles.Cycle,
        };

        // ---------------- Zustand ----------------

        public Dictionary<string, object> Collect()
        {
            var st = new Dictionary<string, object> { ["inGame"] = true };
            var speed = speedManager.CurrentSpeed;
            st["speed"] = speed;
            st["speedLevel"] = SpeedLevel(speed);
            st["paused"] = speed <= 0f;
            st["cycle"] = cycles.Cycle;
            st["day"] = cycles.CycleDay;
            st["hour"] = dayNight.HoursPassedToday;
            st["daytime"] = dayNight.IsDaytime;
            st["settlement"] = Safe(() => settlement.SettlementReference?.SettlementName ?? "");
            st["faction"] = Safe(() => faction.Current?.DisplayName?.Value ?? "");
            st["factionId"] = Safe(() => faction.Current?.Id ?? "");
            CollectWeather(st);
            CollectPopulation(st);
            st["wellbeing"] = wellbeing.AverageGlobalWellbeing;
            st["science"] = science.SciencePoints;
            CollectGoods(st);
            st["notifications"] = CollectHistory();
            st["alerts"] = CollectAlerts();
            return st;
        }

        void CollectWeather(Dictionary<string, object> st)
        {
            var hazardous = weather.IsHazardousWeather;
            var kind = HazardKind(hazards.CurrentCycleHazardousWeather);
            var duration = weather.HazardousWeatherDuration;
            var start = weather.HazardousWeatherStartCycleDay;
            var now = cycles.PartialCycleDay;
            var until = duration > 0 && !hazardous ? Math.Max(0f, start - now) : -1f;
            st["weather"] = hazardous ? kind : "temperate";
            st["weatherName"] = hazardous ? HazardName(kind) : loc.T("Weather.Temperate");
            st["cycleLength"] = weather.CycleLengthInDays;
            st["hazardDays"] = duration;
            st["hazardIn"] = until;                                                     // -1 = keine Gefahr in diesem Zyklus / läuft schon
            st["hazardLeft"] = hazardous ? Math.Max(0f, start + duration - now) : -1f;  // Resttage der laufenden Gefahr
            var reveal = hazardous || (until >= 0f && until <= RevealDays);
            st["hazardNext"] = reveal ? kind : "";
            st["hazardNextName"] = reveal ? HazardName(kind) : "";
        }

        void CollectPopulation(Dictionary<string, object> st)
        {
            var p = population.GlobalPopulationData;
            st["adults"] = p.NumberOfAdults;
            st["children"] = p.NumberOfChildren;
            st["bots"] = p.NumberOfBots;
            st["beavers"] = p.NumberOfBeavers;
            st["population"] = p.TotalPopulation;
            st["homeless"] = p.BedData.Homeless;
            st["freeBeds"] = p.BedData.FreeBeds;
            st["beds"] = p.BedData.OccupiedBeds + p.BedData.FreeBeds;
            st["unemployed"] = p.BeaverWorkplaceData.Unemployed;
            st["freeJobs"] = p.BeaverWorkplaceData.FreeWorkslots + p.BotWorkplaceData.FreeWorkslots;
            st["contaminated"] = p.ContaminationData.ContaminatedTotal;
            lastPopulation = p.TotalPopulation;
        }

        int Population()
        {
            try
            {
                return population.GlobalPopulationData.TotalPopulation;
            }
            catch (Exception)
            {
                return -1;
            }
        }

        /** Bestand, Lagerplatz und Tage, bis der Vorrat beim jetzigen Verbrauch leer ist (aus der Warenstatistik). */
        void CollectGoods(Dictionary<string, object> st)
        {
            var list = new List<object>();
            var food = new Supply();
            var water = new Supply();
            foreach (var id in goods.Goods)
            {
                var spec = goods.GetGoodOrNull(id);
                if (spec == null) continue;
                var rc = resources.GetGlobalResourceCount(spec.Id);
                var s = Sample(spec.Id, rc.AllStock);
                if (spec.GoodGroupId == "Food") food.Add(s);
                if (spec.GoodGroupId == "Water") water.Add(s);
                if (rc.AllStock <= 0 && rc.TotalCapacity <= 0) continue;
                list.Add(new Dictionary<string, object>
                {
                    ["id"] = spec.Id, ["name"] = spec.DisplayName?.Value ?? spec.Id, ["group"] = spec.GoodGroupId ?? "",
                    ["stock"] = rc.AllStock, ["capacity"] = rc.TotalCapacity, ["perDay"] = Math.Round(s.Production - s.Consumption, 1),
                    ["daysLeft"] = Math.Round(s.DaysLeft, 1),
                });
            }
            st["goods"] = list;
            st["food"] = food.Stock;
            st["foodDays"] = Math.Round(food.DaysLeft, 1);
            st["water"] = water.Stock;
            st["waterDays"] = Math.Round(water.DaysLeft, 1);
        }

        class Supply
        {
            public int Stock;
            public double Production, Consumption;

            /** -1 = wird nicht weniger. */
            public double DaysLeft => Consumption > Production ? Stock / (Consumption - Production) : -1;

            public void Add(Supply s)
            {
                Stock += s.Stock;
                Production += s.Production;
                Consumption += s.Consumption;
            }
        }

        /** Durchschnitt der letzten drei Tage aus der Warenstatistik des Spiels. */
        Supply Sample(string goodId, int stock)
        {
            var s = new Supply { Stock = stock };
            try
            {
                var hist = samples.GoodSamplingRegistry.GetGoodSampleHistory(goodId);
                if (hist == null) return s;
                var all = hist.GoodSamples;
                var n = 0;
                for (var i = all.Count - 1; i >= 0 && n < 3; i--, n++)
                {
                    s.Production += all[i].Production;
                    s.Consumption += all[i].Consumption;
                }
                if (n > 0)
                {
                    s.Production /= n;
                    s.Consumption /= n;
                }
            }
            catch (Exception) { /* keine Statistik: nur Bestand */ }
            return s;
        }

        List<object> CollectHistory()
        {
            var list = new List<object>();
            foreach (var n in history)
            {
                list.Add(new Dictionary<string, object>
                {
                    ["text"] = Clean(n.Description), ["cycle"] = n.Cycle, ["day"] = n.CycleDay,
                    ["today"] = n.Cycle == cycles.Cycle && n.CycleDay == cycles.CycleDay,
                    ["canJump"] = n.Subject != Guid.Empty,
                });
            }
            return list;
        }

        /** Aktive Warnungen wie im Warnfeld des Spiels (z. B. „Arbeitslos“), mit Anzahl, die meisten zuerst. */
        List<object> CollectAlerts()
        {
            var list = new List<object>();
            foreach (var kv in VisibleAlerts())
            {
                list.Add(new Dictionary<string, object> { ["text"] = Clean(kv.Key), ["count"] = kv.Value.Count });
            }
            return list;
        }

        List<KeyValuePair<string, IList>> VisibleAlerts()
        {
            var result = new List<KeyValuePair<string, IList>>();
            if (VisibleStatusesField?.GetValue(statuses) is IDictionary dict)
            {
                foreach (DictionaryEntry e in dict)
                {
                    if (e.Key is string text && e.Value is IList l && l.Count > 0 && text.Length > 0)
                        result.Add(new KeyValuePair<string, IList>(text, l));
                }
            }
            result.Sort((a, b) => b.Value.Count != a.Value.Count ? b.Value.Count.CompareTo(a.Value.Count) : string.CompareOrdinal(a.Key, b.Key));
            if (result.Count > AlertSlots) result.RemoveRange(AlertSlots, result.Count - AlertSlots);
            return result;
        }

        // ---------------- Befehle ----------------

        public void Run(Command cmd)
        {
            var a = cmd.Args ?? new Dictionary<string, object>();
            switch (cmd.Name)
            {
                case "pause":
                    Pause(cmd, Json.Str(a, "op", "toggle"));
                    break;
                case "speed":
                    Speed(cmd, Json.Str(a, "op", "set"), (int)Json.Num(a, "value", 1));
                    break;
                case "save":
                    Save(cmd, Json.Str(a, "name", ""));
                    break;
                case "notification":
                    JumpNotification(cmd, (int)Json.Num(a, "n", 1));
                    break;
                case "alert":
                    JumpAlert(cmd, (int)Json.Num(a, "n", 1));
                    break;
                case "message":
                    Message(cmd, Json.Str(a, "text", ""), Json.Str(a, "kind", "info"));
                    break;
                case "refresh":
                    Bridge.RequestState();
                    cmd.Reply(true, "refreshed");
                    break;
                default:
                    cmd.Reply(false, "unknown_command", new Dictionary<string, object> { ["value"] = cmd.Name ?? "" });
                    break;
            }
        }

        void Pause(Command cmd, string op)
        {
            var paused = speedManager.CurrentSpeed <= 0f;
            var want = op == "on" || (op == "toggle" && !paused);
            if (want && !paused)
            {
                speedBeforePause = speedManager.CurrentSpeed;
                speedManager.ChangeSpeed(0f);
            }
            else if (!want && paused)
            {
                speedManager.ChangeSpeed(speedBeforePause > 0f ? speedBeforePause : 1f);
            }
            Bridge.RequestState();
            cmd.Reply(true, want ? "paused" : "resumed");
        }

        /** Stufen wie die Tempo-Knöpfe im Spiel: 1 = ×1, 2 = ×3, 3 = ×7. */
        void Speed(Command cmd, string op, int level)
        {
            var current = SpeedLevel(speedManager.CurrentSpeed);
            if (op == "up") level = Math.Min(Speeds.Length, Math.Max(1, current + 1));
            else if (op == "down") level = Math.Max(1, current - 1);
            if (level < 1 || level > Speeds.Length)
            {
                cmd.Reply(false, "bad_speed", new Dictionary<string, object> { ["value"] = level });
                return;
            }
            speedManager.ChangeSpeed(Speeds[level - 1]);
            Bridge.RequestState();
            cmd.Reply(true, "speed", new Dictionary<string, object> { ["value"] = level, ["factor"] = Speeds[level - 1] });
        }

        static int SpeedLevel(float speed)
        {
            if (speed <= 0f) return 0;
            var best = 1;
            for (var i = 0; i < Speeds.Length; i++)
                if (Math.Abs(Speeds[i] - speed) < Math.Abs(Speeds[best - 1] - speed)) best = i + 1;
            return best;
        }

        void Save(Command cmd, string name)
        {
            name = (name ?? "").Trim();
            if (name.Length == 0) name = "TouchDeck-Quicksave";
            foreach (var c in System.IO.Path.GetInvalidFileNameChars()) name = name.Replace(c, '_');
            var reference = settlement.SettlementReference;
            if (reference == null)
            {
                cmd.Reply(false, "save_failed", new Dictionary<string, object> { ["value"] = "no settlement" });
                return;
            }
            gameSaver.QueueSave(new SaveReference(name, reference), () => Bridge.Log("saved " + name));
            cmd.Reply(true, "saved", new Dictionary<string, object> { ["name"] = name });
        }

        void JumpNotification(Command cmd, int n)
        {
            if (n < 1 || n > history.Count)
            {
                cmd.Reply(false, "no_notification", new Dictionary<string, object> { ["value"] = n });
                return;
            }
            var note = history[n - 1];
            var target = note.Subject != Guid.Empty ? entities.GetEntity(note.Subject) : null;
            if (target == null)
            {
                cmd.Reply(false, "gone", new Dictionary<string, object> { ["name"] = Clean(note.Description) });
                return;
            }
            selection.SelectAndFocusOn(target);
            cmd.Reply(true, "jumped", new Dictionary<string, object> { ["name"] = Clean(note.Description) });
        }

        /** Zu einem Betroffenen der Warnung Nr. n; jedes Tippen nimmt den nächsten. */
        void JumpAlert(Command cmd, int n)
        {
            var alerts = VisibleAlerts();
            if (n < 1 || n > alerts.Count)
            {
                cmd.Reply(false, "no_alert", new Dictionary<string, object> { ["value"] = n });
                return;
            }
            var alert = alerts[n - 1];
            alertCursor.TryGetValue(alert.Key, out var i);
            var count = alert.Value.Count;
            for (var tries = 0; tries < count; tries++, i++)
            {
                if (alert.Value[i % count] is StatusInstance s && s.StatusSubject is BaseComponent subject)
                {
                    alertCursor[alert.Key] = i + 1;
                    selection.SelectAndFocusOn(subject);
                    cmd.Reply(true, "jumped", new Dictionary<string, object>
                    {
                        ["name"] = Clean(alert.Key), ["index"] = i % count + 1, ["count"] = count,
                    });
                    return;
                }
            }
            cmd.Reply(false, "gone", new Dictionary<string, object> { ["name"] = Clean(alert.Key) });
        }

        void Message(Command cmd, string text, string kind)
        {
            text = (text ?? "").Trim();
            if (text.Length == 0)
            {
                cmd.Reply(false, "empty");
                return;
            }
            if (text.Length > 300) text = text.Substring(0, 300);
            if (kind == "warning") quickNotifications.SendWarningNotification(text);
            else quickNotifications.SendNotification(text);
            cmd.Reply(true, "message_shown");
        }

        // ---------------- Hilfen ----------------

        static string HazardKind(IHazardousWeather w)
        {
            var id = w?.Id ?? "";
            if (id.IndexOf("Badtide", StringComparison.OrdinalIgnoreCase) >= 0) return "badtide";
            if (id.IndexOf("Drought", StringComparison.OrdinalIgnoreCase) >= 0) return "drought";
            return id.Length == 0 ? "" : id;
        }

        string HazardName(string kind)
        {
            switch (kind)
            {
                case "drought": return loc.T("Weather.Drought");
                case "badtide": return loc.T("Weather.Badtide");
                default: return kind;
            }
        }

        /** Farb- und Format-Tags des Spiels entfernen, Zeilen zusammenfassen. */
        static string Clean(string text) => Tags.Replace(text ?? "", "").Replace("\r", "").Trim();

        static string Safe(Func<string> f)
        {
            try
            {
                return f() ?? "";
            }
            catch (Exception)
            {
                return "";
            }
        }
    }
}
