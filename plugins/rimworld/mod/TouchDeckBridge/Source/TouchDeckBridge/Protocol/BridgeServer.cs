// Lokaler TCP-Server des Mods. Läuft komplett in eigenen Threads und fasst den Spielzustand nie an:
// Befehle landen in der CommandQueue (abgearbeitet im Hauptthread), Zustand und Ereignisse kommen als
// fertiger Text herein (PublishState, Broadcast). Jeder Client hat einen Lese- und einen Schreib-Thread,
// damit ein langsamer Client weder das Spiel noch andere Clients aufhält.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace TouchDeckBridge.Protocol
{
    public class BridgeServer
    {
        readonly ServerConfig config;
        readonly CommandQueue queue;
        readonly Action<string> log;
        readonly string modVersion;
        readonly string gameVersion;
        readonly object gate = new object();
        readonly List<Client> clients = new List<Client>();
        readonly Stopwatch clock = Stopwatch.StartNew();
        TcpListener listener;
        volatile bool running;
        string lastState;
        long lastSentMs;

        public BridgeServer(ServerConfig config, CommandQueue queue, Action<string> log, string modVersion, string gameVersion)
        {
            this.config = config;
            this.queue = queue;
            this.log = log ?? (_ => { });
            this.modVersion = modVersion;
            this.gameVersion = gameVersion;
        }

        public ServerConfig Config => config;
        public bool Running => running;
        public int ClientCount { get { lock (gate) return clients.Count; } }
        /** Tatsächlicher Port (bei Port 0 in Tests vom System vergeben). */
        public int BoundPort { get; private set; }

        public void Start()
        {
            listener = new TcpListener(config.Address, config.Port);
            listener.Start();
            BoundPort = ((IPEndPoint)listener.LocalEndpoint).Port;
            running = true;
            Spawn("TouchDeckBridge accept", AcceptLoop);
            Spawn("TouchDeckBridge heartbeat", HeartbeatLoop);
            log("listening on " + config.AddressText + ":" + BoundPort);
        }

        public void Stop()
        {
            running = false;
            try { listener?.Stop(); } catch (Exception) { }
            Client[] all;
            lock (gate)
            {
                all = clients.ToArray();
                clients.Clear();
            }
            foreach (var c in all) c.Close();
        }

        /** Voller Zustand als JSON-Zeile; wird nur verschickt, wenn er sich geändert hat. */
        public void PublishState(string line)
        {
            lock (gate)
            {
                if (line == lastState) return;
                lastState = line;
            }
            Broadcast(line);
        }

        public void Broadcast(string line)
        {
            Client[] all;
            lock (gate)
            {
                all = clients.ToArray();
                lastSentMs = clock.ElapsedMilliseconds;
            }
            foreach (var c in all)
                if (!c.Enqueue(line)) Drop(c, "send queue full");
        }

        // ---------------- intern ----------------

        static void Spawn(string name, ThreadStart body)
        {
            new Thread(body) { IsBackground = true, Name = name }.Start();
        }

        void AcceptLoop()
        {
            while (running)
            {
                TcpClient tcp;
                try
                {
                    tcp = listener.AcceptTcpClient();
                }
                catch (Exception e)
                {
                    if (running) log("accept failed: " + e.Message);
                    if (!running) return;
                    Thread.Sleep(200);
                    continue;
                }
                var client = new Client(tcp);
                Spawn("TouchDeckBridge client", () => ClientLoop(client));
            }
        }

        void HeartbeatLoop()
        {
            while (running)
            {
                Thread.Sleep(500);
                bool due;
                lock (gate) due = clock.ElapsedMilliseconds - lastSentMs >= Proto.HeartbeatMs;
                if (due) Broadcast(Proto.Heartbeat);
            }
        }

        void Drop(Client c, string why)
        {
            bool removed;
            lock (gate) removed = clients.Remove(c);
            c.Close();
            if (removed) log("client " + c.Remote + " disconnected (" + why + ")");
        }

        void ClientLoop(Client c)
        {
            try
            {
                c.Tcp.NoDelay = true;
                c.Tcp.ReceiveTimeout = Proto.HelloTimeoutMs;
                c.Tcp.SendTimeout = 3000;
                var reader = new LineReader(c.Tcp.GetStream(), Proto.MaxLine);

                // 1. Hallo
                string first;
                try
                {
                    first = reader.ReadLine();
                }
                catch (IOException)
                {
                    first = null;
                }
                var hello = first == null ? null : Json.TryParseObject(first);
                if (hello == null || Json.Str(hello, "type") != "hello")
                {
                    Deny(c, "hello");
                    return;
                }
                if ((int)Json.Num(hello, "proto", 0) != Proto.Version)
                {
                    Deny(c, "proto");
                    return;
                }
                if (config.Secret.Length > 0 && !Proto.SecretEquals(config.Secret, Json.Str(hello, "secret")))
                {
                    log("client " + c.Remote + " rejected: wrong secret");
                    Deny(c, "secret");
                    return;
                }
                lock (gate)
                {
                    if (clients.Count >= Proto.MaxClients)
                    {
                        Deny(c, "full");
                        return;
                    }
                    clients.Add(c);
                }
                c.Tcp.ReceiveTimeout = 0;
                Spawn("TouchDeckBridge writer", () => WriterLoop(c));
                log("client " + c.Remote + " connected (" + Json.Str(hello, "client", "?") + ")");
                c.Enqueue(Proto.Welcome(modVersion, gameVersion));
                string state;
                lock (gate) state = lastState;
                if (state != null) c.Enqueue(state);

                // 2. Befehle
                while (running && !c.Closed)
                {
                    string line;
                    try
                    {
                        line = reader.ReadLine();
                    }
                    catch (IOException)
                    {
                        break;
                    }
                    if (line == null) break;
                    if (line.Length == 0) continue;
                    var msg = Json.TryParseObject(line);
                    if (msg == null)
                    {
                        log("ignored broken line from " + c.Remote);
                        continue;
                    }
                    switch (Json.Str(msg, "type"))
                    {
                        case "ping":
                            c.Enqueue(Proto.Heartbeat);
                            break;
                        case "cmd":
                            var cmd = new Command
                            {
                                Id = Json.Str(msg, "id"),
                                Name = Json.Str(msg, "cmd"),
                                Args = Json.Obj(msg, "args"),
                                Send = line2 => c.Enqueue(line2),
                            };
                            if (!queue.TryAdd(cmd)) cmd.Reply(false, "busy");
                            break;
                    }
                }
                Drop(c, "closed");
            }
            catch (Exception e)
            {
                Drop(c, e.GetType().Name + ": " + e.Message);
            }
        }

        void Deny(Client c, string reason)
        {
            try
            {
                var bytes = Encoding.UTF8.GetBytes(Proto.Denied(reason) + "\n");
                c.Tcp.GetStream().Write(bytes, 0, bytes.Length);
            }
            catch (Exception) { }
            c.Close();
        }

        void WriterLoop(Client c)
        {
            try
            {
                var stream = c.Tcp.GetStream();
                foreach (var line in c.Outbox.GetConsumingEnumerable())
                {
                    var bytes = Encoding.UTF8.GetBytes(line + "\n");
                    stream.Write(bytes, 0, bytes.Length);
                }
            }
            catch (Exception e)
            {
                Drop(c, "write failed: " + e.Message);
            }
        }

        class Client
        {
            public readonly TcpClient Tcp;
            public readonly string Remote;
            public readonly BlockingCollection<string> Outbox = new BlockingCollection<string>(new ConcurrentQueue<string>());
            volatile bool closed;

            public Client(TcpClient tcp)
            {
                Tcp = tcp;
                try { Remote = tcp.Client.RemoteEndPoint.ToString(); } catch (Exception) { Remote = "?"; }
            }

            public bool Closed => closed;

            /** false, wenn der Client zu weit hinterherhängt (dann wird er getrennt). */
            public bool Enqueue(string line)
            {
                if (closed) return true;
                if (Outbox.Count > 256) return false;
                try { Outbox.Add(line); } catch (InvalidOperationException) { }
                return true;
            }

            public void Close()
            {
                if (closed) return;
                closed = true;
                try { Outbox.CompleteAdding(); } catch (Exception) { }
                try { Tcp.Close(); } catch (Exception) { }
            }
        }
    }

    /** Liest UTF-8-Zeilen; zu lange Zeilen werden bis zum nächsten Zeilenende verworfen (Ergebnis ""). */
    public class LineReader
    {
        readonly Stream stream;
        readonly int maxBytes;
        readonly byte[] buf = new byte[4096];
        int len, pos;
        readonly MemoryStream line = new MemoryStream();
        bool overflow;

        public LineReader(Stream stream, int maxBytes)
        {
            this.stream = stream;
            this.maxBytes = maxBytes;
        }

        /** null = Verbindung zu. */
        public string ReadLine()
        {
            while (true)
            {
                if (pos >= len)
                {
                    len = stream.Read(buf, 0, buf.Length);
                    pos = 0;
                    if (len <= 0) return null;
                }
                var nl = Array.IndexOf(buf, (byte)'\n', pos, len - pos);
                var end = nl < 0 ? len : nl;
                if (!overflow)
                {
                    if (line.Length + (end - pos) > maxBytes)
                    {
                        overflow = true;
                        line.SetLength(0);
                    }
                    else
                    {
                        line.Write(buf, pos, end - pos);
                    }
                }
                pos = end;
                if (nl < 0) continue;
                pos = nl + 1;
                string result;
                if (overflow) result = "";
                else result = Encoding.UTF8.GetString(line.GetBuffer(), 0, (int)line.Length).TrimEnd('\r');
                overflow = false;
                line.SetLength(0);
                return result;
            }
        }
    }
}
