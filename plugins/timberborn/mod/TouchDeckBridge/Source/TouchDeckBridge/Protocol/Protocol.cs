// Protokoll zwischen Mod (TCP-Server) und TouchDeck-Plugin (Client): JSON, eine Nachricht pro Zeile.
//
// Plugin → Mod:
//   {"type":"hello","proto":1,"client":"touchdeck-timberborn/0.1.0","secret":"…"}   (erste Zeile, Pflicht)
//   {"type":"cmd","id":"7","cmd":"speed","args":{"value":2}}                       (Antwort: ack mit derselben id)
//   {"type":"ping"}
// Mod → Plugin:
//   {"type":"welcome","proto":1,"mod":"0.1.0","game":"1.1.2.8"}
//   {"type":"denied","reason":"secret|proto|hello|full"}   danach wird die Verbindung geschlossen
//   {"type":"state","state":{…}}        voller Zustand, nur bei Änderung
//   {"type":"hb"}                       Herzschlag, wenn 5 s lang nichts anderes kam
//   {"type":"event","event":"notification","data":{…}}
//   {"type":"ack","id":"7","ok":true,"code":"speed","args":{…},"msg":"…"}
//
// Keine Timberborn-Typen hier, damit Source/Tests das ohne Spiel prüfen kann.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;

namespace TouchDeckBridge.Protocol
{
    public static class Proto
    {
        public const int Version = 1;
        public const int MaxLine = 64 * 1024;          // längere Zeilen werden verworfen
        public const int HeartbeatMs = 5000;
        public const int HelloTimeoutMs = 5000;
        public const int MaxClients = 4;
        public const int MinRemoteSecret = 12;

        public static string Welcome(string modVersion, string gameVersion) => Json.Serialize(new Dictionary<string, object>
        {
            ["type"] = "welcome", ["proto"] = Version, ["mod"] = modVersion, ["game"] = gameVersion,
        });

        public static string Denied(string reason) => Json.Serialize(new Dictionary<string, object>
        {
            ["type"] = "denied", ["reason"] = reason,
        });

        public static string State(Dictionary<string, object> state) => Json.Serialize(new Dictionary<string, object>
        {
            ["type"] = "state", ["state"] = state,
        });

        public static string Event(string name, Dictionary<string, object> data) => Json.Serialize(new Dictionary<string, object>
        {
            ["type"] = "event", ["event"] = name, ["data"] = data ?? new Dictionary<string, object>(),
        });

        public static string Ack(string id, bool ok, string code, Dictionary<string, object> args, string msg) => Json.Serialize(new Dictionary<string, object>
        {
            ["type"] = "ack", ["id"] = id ?? "", ["ok"] = ok, ["code"] = code ?? "",
            ["args"] = args ?? new Dictionary<string, object>(), ["msg"] = msg ?? "",
        });

        public const string Heartbeat = "{\"type\":\"hb\"}";

        /** Vergleich in konstanter Zeit, damit die Antwortzeit nichts über das Geheimwort verrät. */
        public static bool SecretEquals(string expected, string given)
        {
            expected = expected ?? "";
            given = given ?? "";
            var diff = expected.Length ^ given.Length;
            for (var i = 0; i < expected.Length; i++)
                diff |= expected[i] ^ (i < given.Length ? given[i] : 0);
            return diff == 0;
        }
    }

    /** Geprüfte Server-Einstellungen. Ungültige Eingaben fallen auf den Standard zurück (Meldung in Problems). */
    public class ServerConfig
    {
        public const string DefaultAddress = "127.0.0.1";
        public const int DefaultPort = 34201;

        public IPAddress Address = IPAddress.Loopback;
        public string AddressText = DefaultAddress;
        public int Port = DefaultPort;
        public string Secret = "";
        public readonly List<string> Problems = new List<string>();
        /** Fernzugriff ohne ausreichendes Geheimwort: Server darf nicht starten. */
        public bool Blocked;

        public bool IsLoopback => IPAddress.IsLoopback(Address);

        public static ServerConfig From(string address, string port, string secret)
        {
            var c = new ServerConfig { Secret = (secret ?? "").Trim() };
            var a = (address ?? "").Trim();
            IPAddress ip;
            if (a.Length == 0) a = DefaultAddress;
            if (IPAddress.TryParse(a, out ip) && ip.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork)
            {
                c.Address = ip;
                c.AddressText = ip.ToString();
            }
            else
            {
                c.Problems.Add("invalid address '" + a + "', using " + DefaultAddress);
            }
            int p;
            if (int.TryParse((port ?? "").Trim(), out p) && p >= 1024 && p <= 65535) c.Port = p;
            else c.Problems.Add("invalid port '" + port + "' (1024-65535), using " + DefaultPort);
            if (!c.IsLoopback && c.Secret.Length < Proto.MinRemoteSecret)
            {
                c.Blocked = true;
                c.Problems.Add("address " + c.AddressText + " is reachable from other computers: a secret of at least "
                               + Proto.MinRemoteSecret + " characters is required, server not started");
            }
            return c;
        }

        /** Gleiche Einstellungen? (Bei Änderung startet der Server neu.) */
        public bool SameAs(ServerConfig other) =>
            other != null && other.AddressText == AddressText && other.Port == Port && other.Secret == Secret && other.Blocked == Blocked;
    }

    /** Ein Befehl vom Plugin. Reply wird genau einmal aufgerufen (aus dem Hauptthread). */
    public class Command
    {
        public string Id;
        public string Name;
        public Dictionary<string, object> Args;
        public Action<string> Send;     // schickt eine fertige Zeile an genau diesen Client

        public void Reply(bool ok, string code, Dictionary<string, object> args = null, string msg = "")
        {
            try
            {
                Send?.Invoke(Proto.Ack(Id, ok, code, args, msg));
            }
            catch (Exception) { /* Client weg: egal */ }
            Send = null;
        }
    }

    /** Netzwerk-Thread legt hinein, der Hauptthread holt heraus. Begrenzt, damit ein Client nichts zuschütten kann. */
    public class CommandQueue
    {
        public const int Limit = 64;
        readonly ConcurrentQueue<Command> queue = new ConcurrentQueue<Command>();

        public bool TryAdd(Command c)
        {
            if (queue.Count >= Limit) return false;
            queue.Enqueue(c);
            return true;
        }

        public bool TryTake(out Command c) => queue.TryDequeue(out c);

        public int Count => queue.Count;
    }

    /** Unterdrückt gleiche Ereignisse innerhalb kurzer Zeit (z. B. dieselbe Meldung zweimal hintereinander). */
    public class Deduper
    {
        readonly Dictionary<string, long> seen = new Dictionary<string, long>();
        readonly long windowMs;

        public Deduper(long windowMs) { this.windowMs = windowMs; }

        public bool Allow(string key, long nowMs)
        {
            long last;
            if (seen.TryGetValue(key, out last) && nowMs - last < windowMs) return false;
            seen[key] = nowMs;
            if (seen.Count > 256)
            {
                var old = new List<string>();
                foreach (var kv in seen) if (nowMs - kv.Value >= windowMs) old.Add(kv.Key);
                foreach (var k in old) seen.Remove(k);
            }
            return true;
        }
    }
}
