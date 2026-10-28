// Brücke zum geladenen Spielstand. Holt sich die Dienste des Spiels aus dem DependencyResolver (Initialize des
// Mods). Den Zustand sammelt Collect() im Sync-Schritt des Spiels (IGameLoopEvents.SyncUpdate, Hauptthread,
// Simulation steht dabei kurz) – so lesen auch die Anzeigen des Spiels. Ereignisse aus der Simulation
// (neue Meldung, neuer Monat …) landen erst in einer Warteschlange und werden dort abgearbeitet. Befehle laufen
// aus Bridge.Tick (Hauptthread); ins Spiel gehen sie als Eingabebefehle wie die Knöpfe der Oberfläche.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Mafi;
using Mafi.Core;
using Mafi.Core.Buildings.Settlements;
using Mafi.Core.Entities;
using Mafi.Core.Factory;
using Mafi.Core.Factory.ElectricPower;
using Mafi.Core.GameLoop;
using Mafi.Core.Input;
using Mafi.Core.MessageNotifications;
using Mafi.Core.MessageNotifications.Notifications;
using Mafi.Core.Notifications;
using Mafi.Core.Population;
using Mafi.Core.Products;
using Mafi.Core.Research;
using Mafi.Core.SaveGame;
using Mafi.Core.Simulation;
using Mafi.Unity.Camera;
using Mafi.Unity.InputControl;
using TouchDeckBridge.Protocol;

namespace TouchDeckBridge
{
    public class GameLink
    {
        public const int HistorySize = 8;
        public const int AlertSlots = 8;
        public const int GoodSlots = 8;
        /** Nahrung „knapp“ unter so vielen Monaten (wie das Spiel warnt). */
        public const int LowFoodMonths = 3;
        static readonly Regex Tags = new Regex("<[^>]+>");

        IInputScheduler input;
        readonly IGameLoopEvents loop;
        readonly ISimLoopEvents sim;
        readonly ICalendar calendar;
        IElectricityManager electricity;
        IComputingManager computing;
        UpointsManager unity;
        IWorkersManager workers;
        SettlementsManager settlements;
        PopsHealthManager health;
        ResearchManager research;
        IProductsManager products;
        PinnedProductsManager pinned;
        INotificationsManager notifications;
        IMessageNotificationsManager messages;
        ISaveManager saves;
        CameraController camera;
        GameSpeedController speed;
        /** Für das Nachsuchen fehlender Dienste beim ersten Spieltakt. */
        DependencyResolver resolver;

        /** Aus der Simulation (anderer Thread) → im Sync-Schritt abarbeiten. */
        readonly ConcurrentQueue<Action> pending = new ConcurrentQueue<Action>();
        /** Verlauf: neue Meldungen und Nachrichten, neueste zuerst. */
        readonly List<HistoryEntry> history = new List<HistoryEntry>();
        /** Pro Meldung: welches betroffene Objekt beim nächsten Tippen dran ist. */
        readonly Dictionary<string, int> alertCursor = new Dictionary<string, int>();
        bool powerShort, foodLow, starving;
        string lastDisease = "";
        /** Zuletzt gesehenes Datum, −1 = noch keins. */
        int lastYear = -1, lastMonth = -1;

        public bool Terminated { get; private set; }

        class HistoryEntry
        {
            public string Text;
            public string Kind;      // critical, warning, success, message, research
            public int Year, Month, Day;
            public int Count = 1;
            public IObjectWithTitle Target;
        }

        class Alert
        {
            public string Text;
            public string Style;
            public readonly List<IObjectWithTitle> Targets = new List<IObjectWithTitle>();
        }

        GameLink(DependencyResolver r)
        {
            resolver = r;
            loop = Need<IGameLoopEvents>(r);
            sim = Need<ISimLoopEvents>(r);
            calendar = Need<ICalendar>(r);
            Resolve(false);
        }

        /** Optionale Dienste holen; was fehlt, bleibt null. Warnung erst beim letzten Versuch. */
        void Resolve(bool warn)
        {
            var r = resolver;
            input = input ?? Get<IInputScheduler>(r, warn);
            electricity = electricity ?? Get<IElectricityManager>(r, warn);
            computing = computing ?? Get<IComputingManager>(r, warn);
            unity = unity ?? Get<UpointsManager>(r, warn);
            workers = workers ?? Get<IWorkersManager>(r, warn);
            settlements = settlements ?? Get<SettlementsManager>(r, warn);
            health = health ?? Get<PopsHealthManager>(r, warn);
            research = research ?? Get<ResearchManager>(r, warn);
            products = products ?? Get<IProductsManager>(r, warn);
            pinned = pinned ?? Get<PinnedProductsManager>(r, warn);
            saves = saves ?? Get<ISaveManager>(r, warn);
            camera = camera ?? Get<CameraController>(r, warn);
            speed = speed ?? Get<GameSpeedController>(r, warn);
        }

        static T Get<T>(DependencyResolver r, bool warn = true) where T : class
        {
            try
            {
                var o = r.GetResolvedInstance<T>();
                if (o.HasValue) return o.ValueOrNull;
            }
            catch (Exception) { /* gibt es in dieser Spielversion nicht */ }
            try
            {
                // Manche Dienste sind nur unter ihrer Klasse eingetragen, nicht unter der Schnittstelle.
                foreach (var o in r.AllResolvedInstances)
                    if (o is T t) return t;
            }
            catch (Exception) { }
            if (warn) Bridge.Warn("service not found: " + typeof(T).Name);
            return null;
        }

        static T Need<T>(DependencyResolver r) where T : class =>
            Get<T>(r) ?? throw new InvalidOperationException("required service missing: " + typeof(T).Name);

        /** Aus Initialize des Mods: neuen Spielstand anbinden (alter ist mit dem Laden beendet). */
        public static void Attach(DependencyResolver resolver)
        {
            var link = new GameLink(resolver);
            link.Subscribe();
            Bridge.Game = link;
            Bridge.RequestState();
            Bridge.Log("game loaded");
        }

        void Subscribe()
        {
            notifications = Get<INotificationsManager>(resolver);
            messages = Get<IMessageNotificationsManager>(resolver);
            loop.SyncUpdate.AddNonSaveable(this, OnSync);
            loop.Terminate.AddNonSaveable(this, OnTerminate);
            if (notifications != null) notifications.NotificationAdded += OnNotificationAdded;
            if (messages != null) messages.OnNotificationAdded += OnMessageAdded;
        }

        void OnTerminate()
        {
            Terminated = true;
            try
            {
                if (notifications != null) notifications.NotificationAdded -= OnNotificationAdded;
                if (messages != null) messages.OnNotificationAdded -= OnMessageAdded;
            }
            catch (Exception) { /* Spielstand wird ohnehin abgebaut */ }
            Bridge.RequestState();
            Bridge.Log("game closed");
        }

        // ---------------- Ereignisse aus dem Spiel ----------------

        void OnSync(GameTime time)
        {
            if (Terminated) return;
            if (resolver != null)
            {
                Resolve(true);
                resolver = null;
            }
            for (var i = 0; i < 64 && pending.TryDequeue(out var a); i++)
            {
                try
                {
                    a();
                }
                catch (Exception e)
                {
                    Bridge.Warn("event failed: " + e.Message);
                }
            }
            CheckDate();
            if (Bridge.StateDue()) Bridge.Publish(Collect);
        }

        /** Neuer Monat oder neues Jahr. Nicht über calendar.NewMonth/NewYear: Diese Anmeldungen landen im
         *  Spielstand, und das Spiel kann den Mod dort nicht speichern (Speichern schlägt dann fehl). */
        void CheckDate()
        {
            var d = calendar.CurrentDate;
            if (d.Year == lastYear && d.Month == lastMonth) return;
            var newYear = lastYear >= 0 && d.Year > lastYear;
            lastYear = d.Year;
            lastMonth = d.Month;
            Bridge.RequestState();
            if (newYear) Bridge.Emit("new_year", new Dictionary<string, object> { ["year"] = d.Year });
        }

        void OnNotificationAdded(INotification n) => pending.Enqueue(() =>
        {
            if (n == null || n.Proto == null || n.Proto.HideInNotificationPanel) return;
            var text = Clean(n.Message.Value);
            if (text.Length == 0) return;
            var style = StyleName(n.Proto.Style);
            AddHistory(text, style, n.Object.ValueOrNull);
            Bridge.Emit("notification", new Dictionary<string, object> { ["text"] = text, ["style"] = style }, text);
        });

        void OnMessageAdded(IMessageNotification m) => pending.Enqueue(() =>
        {
            string text, kind = "message";
            switch (m)
            {
                case NewMessageNotification nm:
                    text = Clean(nm.Message?.Title.Value);
                    break;
                case ResearchFinishedMessage rf:
                    text = NodeName(rf.ResearchNode);
                    kind = "research";
                    Bridge.Emit("research_finished", new Dictionary<string, object> { ["name"] = text });
                    break;
                case NewRefugeesMessage nr:
                    text = nr.AmountOfRefugeesAdded.ToString();
                    kind = "refugees";
                    break;
                case GameOverNotification go:
                    text = Clean(go.Title.Value);
                    kind = "game_over";
                    Bridge.Emit("game_over", new Dictionary<string, object> { ["text"] = text });
                    break;
                case LocationExploredMessage _:
                    text = "";
                    kind = "explored";
                    break;
                case ShipInBattleNotification _:
                    text = "";
                    kind = "battle";
                    break;
                default:
                    return;
            }
            AddHistory(text ?? "", kind, null);
            Bridge.Emit("message", new Dictionary<string, object> { ["text"] = text ?? "", ["kind"] = kind });
        });

        void AddHistory(string text, string kind, IObjectWithTitle target)
        {
            var d = calendar.CurrentDate;
            // Dieselbe Meldung gleich noch einmal (z. B. viele Lastwagen ohne Treibstoff): zusammenfassen
            if (history.Count > 0 && history[0].Text == text && history[0].Kind == kind)
            {
                var top = history[0];
                top.Count++;
                top.Year = d.Year;
                top.Month = d.Month;
                top.Day = d.Day;
                if (target != null) top.Target = target;
                return;
            }
            history.Insert(0, new HistoryEntry { Text = text, Kind = kind, Year = d.Year, Month = d.Month, Day = d.Day, Target = target });
            if (history.Count > HistorySize) history.RemoveAt(history.Count - 1);
        }

        // ---------------- Zustand ----------------

        public Dictionary<string, object> Collect()
        {
            var st = new Dictionary<string, object> { ["inGame"] = true };
            var d = calendar.CurrentDate;
            st["year"] = d.Year;
            st["month"] = d.Month;
            st["day"] = d.Day;
            st["monthName"] = Safe(() => d.MonthName);
            CollectSpeed(st);
            CollectPower(st);
            CollectPeople(st);
            CollectResearch(st);
            CollectGoods(st);
            st["alerts"] = CollectAlerts();
            st["history"] = CollectHistory(d);
            st["unreadMessages"] = messages != null ? messages.AllNotifications.Count : 0;
            return st;
        }

        void CollectSpeed(Dictionary<string, object> st)
        {
            var paused = speed != null ? speed.IsPaused : sim.IsSimPaused;
            var mult = speed != null ? speed.SimSpeedMult : sim.SimSpeedMult;
            st["paused"] = paused;
            st["speed"] = mult;
            var levels = Speeds();
            st["speeds"] = new List<object>(Array.ConvertAll(levels, x => (object)x));
            st["speedLevel"] = Array.IndexOf(levels, mult) + 1;   // 0 = Tempo nicht in der Liste
        }

        int[] Speeds()
        {
            try
            {
                if (speed?.Speeds != null && speed.Speeds.Length > 0) return speed.Speeds;
            }
            catch (Exception) { }
            return new[] { 1, 2, 3 };
        }

        void CollectPower(Dictionary<string, object> st)
        {
            if (electricity != null)
            {
                var cap = electricity.GenerationCapacityThisTick.Value;
                var demand = electricity.DemandedThisTick.Value;
                st["powerCapacity"] = cap;
                st["powerDemand"] = demand;
                st["powerUsed"] = electricity.ConsumedThisTick.Value;
                var shortNow = demand > cap && demand > 0;
                if (shortNow && !powerShort) Bridge.Emit("power_short", new Dictionary<string, object> { ["capacity"] = cap, ["demand"] = demand });
                powerShort = shortNow;
            }
            if (computing != null)
            {
                st["computingCapacity"] = computing.GenerationCapacityThisTick.Value;
                st["computingDemand"] = computing.DemandedThisTick.Value;
            }
            if (unity != null)
            {
                // Einheit liegt als Warenmenge im Rohformat vor (80 Einheit = 81920); umrechnen wie das Spiel.
                st["unity"] = Math.Round(unity.Quantity.Upoints().Value.ToFloat(), 1);
                st["unityCap"] = unity.TotalUnityCap.Value.ToFloat();
                st["unityMonth"] = Math.Round(unity.DiffForLastMonth.Value.ToFloat(), 1);
            }
        }

        void CollectPeople(Dictionary<string, object> st)
        {
            if (workers != null)
            {
                var free = workers.AmountOfFreeWorkersOrMissing;
                st["workersFree"] = free;   // negativ = so viele fehlen
            }
            if (settlements != null)
            {
                st["population"] = settlements.GetTotalPopulation();
                st["populationDiff"] = settlements.LastPopulationDiff;
                st["homeless"] = settlements.NumberOfHomeless;
                st["housingFree"] = settlements.FreeHousingCapacity;
                st["housing"] = settlements.TotalHousingCapacity;
                var months = settlements.MonthsOfFood;
                var hungry = settlements.ArePeopleStarving;
                st["foodMonths"] = months;
                st["starving"] = hungry;
                st["starvedLastMonth"] = settlements.AmountStarvedToDeathLastMonth;
                var low = months < LowFoodMonths;
                if (hungry && !starving) Bridge.Emit("starving", new Dictionary<string, object> { ["months"] = months });
                else if (low && !foodLow) Bridge.Emit("food_low", new Dictionary<string, object> { ["months"] = months });
                foodLow = low;
                starving = hungry;
            }
            if (health != null)
            {
                var disease = health.CurrentDisease.HasValue ? Clean(health.CurrentDisease.ValueOrNull.Strings.Name.TranslatedString) : "";
                st["disease"] = disease;
                st["diseaseMonths"] = disease.Length > 0 ? health.CurrentDiseaseMonthsLeft : 0;
                if (disease.Length > 0 && disease != lastDisease) Bridge.Emit("disease", new Dictionary<string, object> { ["name"] = disease });
                lastDisease = disease;
            }
        }

        void CollectResearch(Dictionary<string, object> st)
        {
            if (research == null) return;
            var cur = research.CurrentResearch;
            var name = cur.HasValue ? NodeName(cur.ValueOrNull) : "";
            st["research"] = name;
            st["researchProgress"] = cur.HasValue ? cur.ValueOrNull.ProgressInPerc.IntegerPart : 0;
            st["researchQueue"] = research.ResearchQueue.Count;
            st["researchLab"] = research.HasActiveLab;
        }

        /** Angeheftete Waren zuerst (wie die Liste rechts im Spiel), dann die mit dem größten Bestand. */
        void CollectGoods(Dictionary<string, object> st)
        {
            if (products == null) return;
            var all = new List<object>();
            var stats = new List<ProductStats>();
            foreach (var s in products.ProductStats)
            {
                if (s?.Product == null || IsVirtual(s.Product)) continue;
                if (s.StoredQuantityTotal.Value <= 0 && s.StorageCapacity.Value <= 0) continue;
                stats.Add(s);
                all.Add(Good(s, false));
            }
            var slots = new List<object>();
            var used = new HashSet<string>();
            if (pinned != null)
            {
                foreach (var p in pinned.AllPinnedProducts)
                {
                    if (slots.Count >= GoodSlots) break;
                    var s = products.GetStatsFor(p);
                    if (s == null || IsVirtual(s.Product)) continue;
                    used.Add(p.Id.Value);
                    slots.Add(Good(s, true));
                }
            }
            stats.Sort((a, b) => b.StoredQuantityTotal.Value.CompareTo(a.StoredQuantityTotal.Value));
            foreach (var s in stats)
            {
                if (slots.Count >= GoodSlots) break;
                if (used.Add(s.Product.Id.Value)) slots.Add(Good(s, false));
            }
            st["goods"] = all;
            st["goodSlots"] = slots;
        }

        /** Keine echten Waren: Einheit, Wartung … (stehen als Waren in der Statistik, aber nicht im Lager). */
        static bool IsVirtual(ProductProto p) =>
            p is VirtualProductProto || p.Id.Value.StartsWith("Virtual_", StringComparison.Ordinal);

        static Dictionary<string, object> Good(ProductStats s, bool pin) => new Dictionary<string, object>
        {
            ["id"] = ProductId(s.Product.Id.Value),
            ["name"] = Clean(s.Product.Strings.Name.TranslatedString),
            ["stock"] = s.StoredQuantityTotal.Value,
            ["capacity"] = s.StorageCapacity.Value,
            ["perMonth"] = s.CreatedTotalStats.LastMonth.Value - s.UsedTotalStats.LastMonth.Value,
            ["pinned"] = pin,
        };

        /** „Product_IronOre“ → „IronOre“ (für Wertnamen). */
        static string ProductId(string id)
        {
            id = id ?? "";
            if (id.StartsWith("Product_", StringComparison.Ordinal)) id = id.Substring(8);
            return Regex.Replace(id, "[^A-Za-z0-9_]", "");
        }

        /** Aktive Meldungen wie im Meldungsfeld des Spiels: gleiche Texte zusammengefasst, kritische zuerst. */
        List<Alert> ActiveAlerts()
        {
            var byText = new Dictionary<string, Alert>();
            var list = new List<Alert>();
            if (notifications == null) return list;
            foreach (var n in notifications.FetchAllNotifications())
            {
                if (n == null || n.IsSuppressed || n.Proto == null || n.Proto.HideInNotificationPanel) continue;
                var text = Clean(n.Message.Value);
                if (text.Length == 0) continue;
                if (!byText.TryGetValue(text, out var a))
                {
                    a = new Alert { Text = text, Style = StyleName(n.Proto.Style) };
                    byText[text] = a;
                    list.Add(a);
                }
                a.Targets.Add(n.Object.ValueOrNull);
            }
            list.Sort((x, y) =>
            {
                var r = Rank(y.Style).CompareTo(Rank(x.Style));
                if (r != 0) return r;
                r = y.Targets.Count.CompareTo(x.Targets.Count);
                return r != 0 ? r : string.CompareOrdinal(x.Text, y.Text);
            });
            return list;
        }

        List<object> CollectAlerts()
        {
            var list = new List<object>();
            var all = ActiveAlerts();
            for (var i = 0; i < all.Count && i < AlertSlots; i++)
            {
                var a = all[i];
                list.Add(new Dictionary<string, object> { ["text"] = a.Text, ["style"] = a.Style, ["count"] = a.Targets.Count });
            }
            return list;
        }

        List<object> CollectHistory(GameDate now)
        {
            var list = new List<object>();
            foreach (var h in history)
            {
                list.Add(new Dictionary<string, object>
                {
                    ["text"] = h.Text, ["kind"] = h.Kind, ["count"] = h.Count, ["year"] = h.Year, ["month"] = h.Month,
                    ["today"] = h.Year == now.Year && h.Month == now.Month, ["canJump"] = Position(h.Target) != null,
                });
            }
            return list;
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
                case "alert":
                    JumpAlert(cmd, (int)Json.Num(a, "n", 1));
                    break;
                case "history":
                    JumpHistory(cmd, (int)Json.Num(a, "n", 1));
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

        bool IsPaused => speed != null ? speed.IsPaused : sim.IsSimPaused;

        void Pause(Command cmd, string op)
        {
            var want = op == "on" || (op == "toggle" && !IsPaused);
            if (want != IsPaused)
            {
                if (speed != null)
                {
                    if (want) speed.RequestPause();
                    else speed.RequestResume();
                }
                else if (input != null) input.ScheduleInputCmd(new SetSimPauseStateCmd(want));
                else
                {
                    cmd.Reply(false, "unsupported");
                    return;
                }
            }
            Bridge.RequestState();
            cmd.Reply(true, want ? "paused" : "resumed");
        }

        /** Stufen wie die Tempo-Knöpfe im Spiel (Stufe 1 = ×1 …). Hebt die Pause auf. */
        void Speed(Command cmd, string op, int level)
        {
            var levels = Speeds();
            var mult = speed != null ? speed.SimSpeedMult : sim.SimSpeedMult;
            var current = Math.Max(1, Array.IndexOf(levels, mult) + 1);
            if (op == "up") level = Math.Min(levels.Length, current + 1);
            else if (op == "down") level = Math.Max(1, current - 1);
            if (level < 1 || level > levels.Length)
            {
                cmd.Reply(false, "bad_speed", new Dictionary<string, object> { ["value"] = level, ["max"] = levels.Length });
                return;
            }
            var factor = levels[level - 1];
            if (speed != null)
            {
                speed.SetSpeed(factor);
                if (speed.IsPaused) speed.RequestResume();
            }
            else if (input == null)
            {
                cmd.Reply(false, "unsupported");
                return;
            }
            else
            {
                input.ScheduleInputCmd(new GameSpeedChangeCmd(factor));
                if (sim.IsSimPaused) input.ScheduleInputCmd(new SetSimPauseStateCmd(false));
            }
            Bridge.RequestState();
            cmd.Reply(true, "speed", new Dictionary<string, object> { ["value"] = level, ["factor"] = factor });
        }

        void Save(Command cmd, string name)
        {
            if (saves == null)
            {
                cmd.Reply(false, "save_failed", new Dictionary<string, object> { ["value"] = "no save manager" });
                return;
            }
            if (saves.IsNonAutosaveInProgress())
            {
                cmd.Reply(false, "busy");
                return;
            }
            name = (name ?? "").Trim();
            if (name.Length == 0) name = "TouchDeck-Quicksave";
            foreach (var c in System.IO.Path.GetInvalidFileNameChars()) name = name.Replace(c, '_');
            saves.RequestGameSave(name);
            cmd.Reply(true, "saved", new Dictionary<string, object> { ["name"] = name });
        }

        /** Kamera zu einem Betroffenen der Meldung Nr. n; jedes Tippen nimmt den nächsten. */
        void JumpAlert(Command cmd, int n)
        {
            var alerts = ActiveAlerts();
            if (n < 1 || n > alerts.Count)
            {
                cmd.Reply(false, "no_alert", new Dictionary<string, object> { ["value"] = n });
                return;
            }
            var alert = alerts[n - 1];
            alertCursor.TryGetValue(alert.Text, out var i);
            var count = alert.Targets.Count;
            for (var tries = 0; tries < count; tries++, i++)
            {
                var pos = Position(alert.Targets[i % count]);
                if (pos == null) continue;
                alertCursor[alert.Text] = i + 1;
                if (!PanTo(pos.Value))
                {
                    cmd.Reply(false, "no_camera");
                    return;
                }
                cmd.Reply(true, "jumped", new Dictionary<string, object> { ["name"] = alert.Text, ["index"] = i % count + 1, ["count"] = count });
                return;
            }
            cmd.Reply(false, "no_place", new Dictionary<string, object> { ["name"] = alert.Text });
        }

        void JumpHistory(Command cmd, int n)
        {
            if (n < 1 || n > history.Count)
            {
                cmd.Reply(false, "no_history", new Dictionary<string, object> { ["value"] = n });
                return;
            }
            var h = history[n - 1];
            var pos = Position(h.Target);
            if (pos == null)
            {
                cmd.Reply(false, "no_place", new Dictionary<string, object> { ["name"] = h.Text });
                return;
            }
            if (!PanTo(pos.Value))
            {
                cmd.Reply(false, "no_camera");
                return;
            }
            cmd.Reply(true, "jumped", new Dictionary<string, object> { ["name"] = h.Text });
        }

        bool PanTo(Tile2f pos)
        {
            if (camera == null) return false;
            camera.PanTo(pos);
            return true;
        }

        // ---------------- Hilfen ----------------

        /** Position eines Objekts, wenn es noch existiert und eine hat (Gebäude, Fahrzeug …). */
        static Tile2f? Position(IObjectWithTitle o)
        {
            try
            {
                if (o is IEntity e && e.IsDestroyed) return null;
                if (o is IEntityWithPosition p) return p.Position2f;
            }
            catch (Exception) { }
            return null;
        }

        static string NodeName(ResearchNode node)
        {
            try
            {
                return node == null ? "" : Clean(node.Proto.Strings.Name.TranslatedString);
            }
            catch (Exception)
            {
                return "";
            }
        }

        static string StyleName(NotificationStyle s)
        {
            switch (s)
            {
                case NotificationStyle.Critical: return "critical";
                case NotificationStyle.Success: return "success";
                default: return "warning";
            }
        }

        static int Rank(string style) => style == "critical" ? 2 : style == "warning" ? 1 : 0;

        /** Format-Tags des Spiels entfernen, Zeilen zusammenfassen. */
        static string Clean(string text) => Tags.Replace(text ?? "", "").Replace("\r", "").Replace("\n", " ").Trim();

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
