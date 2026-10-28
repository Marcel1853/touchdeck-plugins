// Tests für die spielunabhängigen Teile (JSON, Protokoll, TCP-Server). Ohne Test-Framework, damit nichts
// heruntergeladen werden muss. Aufruf: Source/Tests/run.sh (übersetzt mit mcs, startet mit mono).
using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using TouchDeckBridge.Protocol;

static class ProtocolTests
{
    static int failed, passed;

    static void Check(bool ok, string what)
    {
        if (ok) passed++;
        else
        {
            failed++;
            Console.WriteLine("FEHLER: " + what);
        }
    }

    static void Throws(Action a, string what)
    {
        try
        {
            a();
            Check(false, what + " (keine Ausnahme)");
        }
        catch (JsonException)
        {
            Check(true, what);
        }
    }

    static int Main(string[] args)
    {
        if (args.Length == 2 && args[0] == "--serve") return Serve(int.Parse(args[1]));
        JsonTests();
        ConfigTests();
        HelperTests();
        LineReaderTests();
        ServerTests();
        Console.WriteLine(passed + " bestanden, " + failed + " fehlgeschlagen");
        return failed == 0 ? 0 : 1;
    }

    static void JsonTests()
    {
        // Rundreise mit Grenzfällen: Anführungszeichen, Umlaute, Zeilenumbrüche, Steuerzeichen, Emoji
        var tricky = "Er sagte \"Hallo\"\nÄÖÜ äöü ß \\ / \t \u0001 \u2028 🐿️";
        var obj = new Dictionary<string, object>
        {
            ["text"] = tricky, ["n"] = 3, ["f"] = 2.5, ["neg"] = -0.125, ["big"] = 12345678901L,
            ["t"] = true, ["no"] = false, ["nul"] = null, ["nan"] = double.NaN,
            ["list"] = new List<object> { 1, "zwei", new Dictionary<string, object> { ["drei"] = 3 } },
            ["leer"] = new Dictionary<string, object>(), ["leereListe"] = new List<object>(),
        };
        var text = Json.Serialize(obj);
        Check(!text.Contains("\n"), "Serialisiert ohne echten Zeilenumbruch (eine Nachricht pro Zeile)");
        Check(text.Contains("ÄÖÜ"), "Umlaute bleiben lesbar");
        Check(text.Contains("\\u2028"), "U+2028 wird maskiert");
        var back = (Dictionary<string, object>)Json.Parse(text);
        Check((string)back["text"] == tricky, "String-Rundreise");
        Check((double)back["n"] == 3 && (double)back["f"] == 2.5 && (double)back["neg"] == -0.125, "Zahlen");
        Check((double)back["big"] == 12345678901d, "große Zahl");
        Check((bool)back["t"] && !(bool)back["no"] && back["nul"] == null && back["nan"] == null, "bool/null/NaN");
        var list = (List<object>)back["list"];
        Check(list.Count == 3 && (string)list[1] == "zwei" && (double)((Dictionary<string, object>)list[2])["drei"] == 3, "verschachtelt");
        Check(((Dictionary<string, object>)back["leer"]).Count == 0 && ((List<object>)back["leereListe"]).Count == 0, "leere Container");

        // Escapes von außen
        var parsed = (Dictionary<string, object>)Json.Parse("{ \"a\" : \"x\\u00e4\\ud83d\\ude00\\/\\n\" , \"b\":[ ] }");
        Check((string)parsed["a"] == "xä😀/\n", "\\u-Escapes inkl. Surrogatpaar");
        Check(Math.Abs((double)Json.Parse("-1.5e3") + 1500) < 1e-9, "Exponent");

        Throws(() => Json.Parse("{\"a\":1"), "abgeschnittenes Objekt");
        Throws(() => Json.Parse("{\"a\":1}x"), "Müll am Ende");
        Throws(() => Json.Parse("\"offen"), "offener String");
        Throws(() => Json.Parse("{'a':1}"), "einfache Anführungszeichen");
        Throws(() => Json.Parse("[1,]"), "Komma am Ende");
        Throws(() => Json.Parse("\"a\nb\""), "roher Zeilenumbruch im String");
        Throws(() => Json.Parse("\"\\x\""), "unbekanntes Escape");
        Throws(() => Json.Parse(""), "leer");
        Throws(() => Json.Parse(new string('[', 100) + new string(']', 100)), "zu tief");
        Check(Json.TryParseObject("[1,2]") == null, "TryParseObject: Liste ist kein Objekt");
        Check(Json.TryParseObject("kaputt") == null, "TryParseObject: kaputt");

        var m = Json.TryParseObject("{\"s\":\"x\",\"n\":\"2,5\",\"b\":\"ja\",\"o\":{\"k\":1}}");
        Check(Json.Str(m, "s") == "x" && Json.Str(m, "fehlt", "d") == "d", "Str");
        Check(Json.Num(m, "n", 0) == 2.5 && Json.Num(m, "s", 7) == 7, "Num mit Komma und Rückfall");
        Check(Json.Bool(m, "b", false) && !Json.Bool(m, "fehlt", false), "Bool");
        Check(Json.Obj(m, "o").Count == 1 && Json.Obj(m, "s").Count == 0, "Obj");
    }

    static void ConfigTests()
    {
        var c = ServerConfig.From("127.0.0.1", "34202", "");
        Check(c.Problems.Count == 0 && !c.Blocked && c.IsLoopback && c.Port == 34202, "Standard ist gültig");
        c = ServerConfig.From("kaputt", "80", "");
        Check(c.AddressText == "127.0.0.1" && c.Port == 34202 && c.Problems.Count == 2, "ungültige Adresse und Port → Standard");
        c = ServerConfig.From("0.0.0.0", "34202", "kurz");
        Check(c.Blocked, "Fernzugriff ohne langes Geheimwort blockiert");
        c = ServerConfig.From("192.168.1.5", "34202", "ein-langes-geheimwort");
        Check(!c.Blocked && !c.IsLoopback && c.Port == 34202, "Fernzugriff mit Geheimwort erlaubt");
        c = ServerConfig.From("::1", "34202", "");
        Check(c.AddressText == "127.0.0.1", "IPv6 wird nicht angenommen (Rückfall)");
        Check(ServerConfig.From("127.0.0.1", "1", "a").SameAs(ServerConfig.From("127.0.0.1", "x", "a")), "SameAs");
    }

    static void HelperTests()
    {
        Check(Proto.SecretEquals("abc", "abc") && !Proto.SecretEquals("abc", "abd") && !Proto.SecretEquals("abc", "ab")
              && !Proto.SecretEquals("abc", "abcd") && Proto.SecretEquals("", null), "SecretEquals");
        var d = new Deduper(3000);
        Check(d.Allow("raid", 0) && !d.Allow("raid", 1000) && d.Allow("raid", 3500) && d.Allow("other", 1000), "Deduper");
        var q = new CommandQueue();
        for (var i = 0; i < CommandQueue.Limit; i++) q.TryAdd(new Command());
        Check(!q.TryAdd(new Command()), "Warteschlange begrenzt");
        var replies = new List<string>();
        var cmd = new Command { Id = "7", Send = replies.Add };
        cmd.Reply(true, "speed", new Dictionary<string, object> { ["value"] = 2 });
        cmd.Reply(true, "doppelt");
        Check(replies.Count == 1 && replies[0].Contains("\"id\":\"7\"") && replies[0].Contains("\"ok\":true"), "genau eine Antwort");
    }

    static void LineReaderTests()
    {
        var data = "eins\r\nzwei\n" + new string('x', 200) + "\ndrei äöü\n" + "rest";
        var r = new LineReader(new MemoryStream(Encoding.UTF8.GetBytes(data)), 100);
        Check(r.ReadLine() == "eins" && r.ReadLine() == "zwei", "Zeilen, CRLF");
        Check(r.ReadLine() == "", "zu lange Zeile verworfen");
        Check(r.ReadLine() == "drei äöü", "danach geht es weiter, UTF-8");
        Check(r.ReadLine() == null, "unvollständige letzte Zeile = Ende");
    }

    // ---------------- echter TCP-Server ----------------

    class TestClient : IDisposable
    {
        public readonly TcpClient Tcp;
        readonly LineReader reader;

        public TestClient(int port)
        {
            Tcp = new TcpClient("127.0.0.1", port) { ReceiveTimeout = 3000 };
            reader = new LineReader(Tcp.GetStream(), Proto.MaxLine);
        }

        public void Send(string line)
        {
            var b = Encoding.UTF8.GetBytes(line + "\n");
            Tcp.GetStream().Write(b, 0, b.Length);
        }

        public Dictionary<string, object> Next(string type = null)
        {
            while (true)
            {
                string line;
                try { line = reader.ReadLine(); } catch (IOException) { return null; }
                if (line == null) return null;
                var m = Json.TryParseObject(line);
                if (type == null || Json.Str(m, "type") == type) return m;
            }
        }

        public void Dispose() => Tcp.Close();
    }

    static void ServerTests()
    {
        var logs = new List<string>();
        var queue = new CommandQueue();
        var cfg = ServerConfig.From("127.0.0.1", "34202", "geheim");
        cfg.Port = 0; // freier Port
        var server = new BridgeServer(cfg, queue, s => { lock (logs) logs.Add(s); }, "0.1.0", "test");
        server.Start();
        var port = server.BoundPort;
        server.PublishState(Proto.State(new Dictionary<string, object> { ["inGame"] = false }));

        using (var c = new TestClient(port))
        {
            c.Send("{\"type\":\"hello\",\"proto\":1,\"secret\":\"falsch\"}");
            var m = c.Next();
            Check(Json.Str(m, "type") == "denied" && Json.Str(m, "reason") == "secret", "falsches Geheimwort abgelehnt");
            Check(c.Next() == null, "danach Verbindung zu");
        }
        using (var c = new TestClient(port))
        {
            c.Send("{\"type\":\"hello\",\"proto\":99,\"secret\":\"geheim\"}");
            Check(Json.Str(c.Next(), "reason") == "proto", "falsche Protokollversion abgelehnt");
        }
        using (var c = new TestClient(port))
        {
            c.Send("kein json");
            Check(Json.Str(c.Next(), "reason") == "hello", "ohne Hallo abgelehnt");
        }

        using (var c = new TestClient(port))
        {
            c.Send("{\"type\":\"hello\",\"proto\":1,\"client\":\"test\",\"secret\":\"geheim\"}");
            var w = c.Next();
            Check(Json.Str(w, "type") == "welcome" && Json.Str(w, "mod") == "0.1.0", "Willkommen");
            var s = c.Next();
            Check(Json.Str(s, "type") == "state" && !Json.Bool(Json.Obj(s, "state"), "inGame", true), "Zustand direkt nach dem Hallo");

            // Befehl → Warteschlange → Antwort aus „Hauptthread“
            c.Send("kaputt {");
            c.Send(new string('y', Proto.MaxLine + 10));
            c.Send("{\"type\":\"cmd\",\"id\":\"c1\",\"cmd\":\"speed\",\"args\":{\"value\":2,\"text\":\"Grüße\\n\"}}");
            Command cmd = null;
            for (var i = 0; i < 100 && !queue.TryTake(out cmd); i++) Thread.Sleep(20);
            Check(cmd != null && cmd.Name == "speed" && Json.Num(cmd.Args, "value", 0) == 2 && Json.Str(cmd.Args, "text") == "Grüße\n",
                  "Befehl kommt trotz kaputter und zu langer Zeilen an");
            cmd?.Reply(true, "speed", new Dictionary<string, object> { ["value"] = 2 }, "Speed 2");
            var ack = c.Next("ack");
            Check(Json.Str(ack, "id") == "c1" && Json.Bool(ack, "ok", false) && Json.Str(ack, "code") == "speed", "Antwort mit id");

            // Zustand nur bei Änderung
            server.PublishState(Proto.State(new Dictionary<string, object> { ["inGame"] = true }));
            server.PublishState(Proto.State(new Dictionary<string, object> { ["inGame"] = true }));
            server.Broadcast(Proto.Event("notification", new Dictionary<string, object> { ["text"] = "Dürre beginnt" }));
            var st = c.Next("state");
            Check(Json.Bool(Json.Obj(st, "state"), "inGame", false), "neuer Zustand kommt an");
            var ev = c.Next();
            Check(Json.Str(ev, "type") == "event" && Json.Str(Json.Obj(ev, "data"), "text") == "Dürre beginnt",
                  "gleicher Zustand nicht doppelt, Ereignis direkt danach");

            // Herzschlag nach 5 s Ruhe
            c.Tcp.ReceiveTimeout = 7000;
            Check(Json.Str(c.Next(), "type") == "hb", "Herzschlag");

            c.Send("{\"type\":\"ping\"}");
            Check(Json.Str(c.Next(), "type") == "hb", "Ping wird beantwortet");
            Check(server.ClientCount == 1, "ein Client verbunden");
        }
        Thread.Sleep(300);
        Check(server.ClientCount == 0, "Client nach Trennen entfernt");

        // höchstens MaxClients gleichzeitig
        var many = new List<TestClient>();
        for (var i = 0; i < Proto.MaxClients; i++)
        {
            var c = new TestClient(port);
            c.Send("{\"type\":\"hello\",\"proto\":1,\"secret\":\"geheim\"}");
            c.Next("welcome");
            many.Add(c);
        }
        using (var extra = new TestClient(port))
        {
            extra.Send("{\"type\":\"hello\",\"proto\":1,\"secret\":\"geheim\"}");
            Check(Json.Str(extra.Next(), "reason") == "full", "zu viele Clients abgelehnt");
        }
        server.Stop();
        foreach (var c in many)
        {
            Check(c.Next("nie") == null, "Stop trennt alle Clients");
            c.Dispose();
        }
        try
        {
            using (new TcpClient("127.0.0.1", port)) { }
            Check(false, "Port nach Stop noch offen");
        }
        catch (SocketException)
        {
            Check(true, "Port nach Stop geschlossen");
        }
    }

    // ---------------- Server ohne Spiel (für tests/test_real_server.py im Plugin) ----------------

    /** Echter BridgeServer mit festem Zustand; Befehle werden wie im Spiel im „Hauptthread“ beantwortet. */
    static int Serve(int port)
    {
        var queue = new CommandQueue();
        var cfg = ServerConfig.From("127.0.0.1", port.ToString(), "");
        var server = new BridgeServer(cfg, queue, s => Console.Error.WriteLine(s), "0.1.0", "ohne Spiel");
        server.Start();
        var paused = false;
        Console.WriteLine("ready " + server.BoundPort);
        Console.Out.Flush();
        while (true)
        {
            server.PublishState(Proto.State(new Dictionary<string, object>
            {
                ["inGame"] = true, ["speed"] = paused ? 0f : 3f, ["speedLevel"] = 2, ["paused"] = paused, ["cycle"] = 2,
                ["day"] = 7, ["hour"] = 6.25, ["daytime"] = true, ["weatherName"] = "Dürre", ["weather"] = "drought",
                ["hazardIn"] = -1f, ["hazardLeft"] = 1.5f, ["hazardDays"] = 3, ["hazardNextName"] = "Dürre", ["cycleLength"] = 12,
                ["beavers"] = 12, ["adults"] = 9, ["children"] = 3, ["homeless"] = 1, ["water"] = 40, ["waterDays"] = 0.8,
                ["goods"] = new List<object>
                {
                    new Dictionary<string, object> { ["id"] = "Log", ["name"] = "Rohholz", ["stock"] = 50, ["capacity"] = 100, ["perDay"] = 2.5 },
                },
                ["notifications"] = new List<object>
                {
                    new Dictionary<string, object> { ["text"] = "Zoë „Ärni“ ist da", ["cycle"] = 2, ["day"] = 7, ["today"] = true },
                },
                ["alerts"] = new List<object> { new Dictionary<string, object> { ["text"] = "Durstig", ["count"] = 4 } },
            }));
            while (queue.TryTake(out var cmd))
            {
                if (cmd.Name == "pause")
                {
                    paused = !paused;
                    cmd.Reply(true, paused ? "paused" : "resumed");
                }
                else if (cmd.Name == "notification")
                {
                    server.Broadcast(Proto.Event("notification", new Dictionary<string, object>
                    {
                        ["text"] = "Biber „Kalle“ ist gestorben\nZeile 2", ["cycle"] = 3, ["day"] = 5, ["warning"] = true,
                    }));
                    cmd.Reply(true, "jumped", new Dictionary<string, object> { ["name"] = "Zoë „Ärni“ ist da" });
                }
                else cmd.Reply(false, "unknown_command", new Dictionary<string, object> { ["value"] = cmd.Name });
            }
            Thread.Sleep(50);
        }
    }
}
