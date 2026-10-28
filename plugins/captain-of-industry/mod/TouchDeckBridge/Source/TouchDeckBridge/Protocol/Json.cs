// Kleiner JSON-Serialisierer und -Parser für das TouchDeck-Protokoll.
// Eigener kleiner JSON-Leser/-Schreiber: kein fremdes Paket mitliefern, keine Abhängigkeit von der Spielversion.
// Unterstützt: Objekte (Dictionary<string, object>), Listen, Strings, Zahlen (double/long/int), Booleans, null.
// Keine Spiel-Typen, damit es ohne Spiel getestet werden kann (Source/Tests).
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace TouchDeckBridge.Protocol
{
    public class JsonException : Exception
    {
        public JsonException(string message) : base(message) { }
    }

    public static class Json
    {
        public const int MaxDepth = 32;

        // ---------------- Schreiben ----------------

        public static string Serialize(object value)
        {
            var sb = new StringBuilder(256);
            Write(sb, value, 0);
            return sb.ToString();
        }

        static void Write(StringBuilder sb, object value, int depth)
        {
            if (depth > MaxDepth) throw new JsonException("too deep");
            switch (value)
            {
                case null:
                    sb.Append("null");
                    return;
                case string s:
                    WriteString(sb, s);
                    return;
                case bool b:
                    sb.Append(b ? "true" : "false");
                    return;
                case double d:
                    WriteDouble(sb, d);
                    return;
                case float f:
                    WriteDouble(sb, f);
                    return;
                case int i:
                    sb.Append(i.ToString(CultureInfo.InvariantCulture));
                    return;
                case long l:
                    sb.Append(l.ToString(CultureInfo.InvariantCulture));
                    return;
                case IDictionary<string, object> obj:
                    sb.Append('{');
                    var first = true;
                    foreach (var kv in obj)
                    {
                        if (!first) sb.Append(',');
                        first = false;
                        WriteString(sb, kv.Key);
                        sb.Append(':');
                        Write(sb, kv.Value, depth + 1);
                    }
                    sb.Append('}');
                    return;
                case IEnumerable list:
                    sb.Append('[');
                    var firstItem = true;
                    foreach (var item in list)
                    {
                        if (!firstItem) sb.Append(',');
                        firstItem = false;
                        Write(sb, item, depth + 1);
                    }
                    sb.Append(']');
                    return;
                default:
                    if (value is IConvertible c)
                    {
                        // übrige Zahlentypen (short, byte, decimal …) als double
                        try
                        {
                            WriteDouble(sb, c.ToDouble(CultureInfo.InvariantCulture));
                            return;
                        }
                        catch (Exception) { /* unten als Text */ }
                    }
                    WriteString(sb, value.ToString());
                    return;
            }
        }

        static void WriteDouble(StringBuilder sb, double d)
        {
            // NaN und Unendlich gibt es in JSON nicht
            if (double.IsNaN(d) || double.IsInfinity(d)) sb.Append("null");
            else sb.Append(d.ToString("R", CultureInfo.InvariantCulture));
        }

        static void WriteString(StringBuilder sb, string s)
        {
            sb.Append('"');
            foreach (var ch in s)
            {
                switch (ch)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    case '\b': sb.Append("\\b"); break;
                    case '\f': sb.Append("\\f"); break;
                    default:
                        // Steuerzeichen und die JS-Zeilentrenner maskieren, alles andere (ä, ö, ü …) bleibt UTF-8
                        if (ch < 0x20 || ch == (char)0x2028 || ch == (char)0x2029)
                            sb.Append("\\u").Append(((int)ch).ToString("x4"));
                        else
                            sb.Append(ch);
                        break;
                }
            }
            sb.Append('"');
        }

        // ---------------- Lesen ----------------

        public static object Parse(string text)
        {
            if (text == null) throw new JsonException("null input");
            var p = new Parser(text);
            p.SkipWs();
            var value = p.ReadValue(0);
            p.SkipWs();
            if (!p.AtEnd) throw new JsonException("trailing characters at " + p.Pos);
            return value;
        }

        /** Parsen ohne Ausnahme: null bei kaputtem Text oder wenn es kein Objekt ist. */
        public static Dictionary<string, object> TryParseObject(string text)
        {
            try
            {
                return Parse(text) as Dictionary<string, object>;
            }
            catch (JsonException)
            {
                return null;
            }
        }

        sealed class Parser
        {
            readonly string s;
            int i;

            public Parser(string text) { s = text; }

            public int Pos => i;
            public bool AtEnd => i >= s.Length;

            public void SkipWs()
            {
                while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) i++;
            }

            char Peek()
            {
                if (i >= s.Length) throw new JsonException("unexpected end");
                return s[i];
            }

            public object ReadValue(int depth)
            {
                if (depth > MaxDepth) throw new JsonException("too deep");
                var c = Peek();
                switch (c)
                {
                    case '{': return ReadObject(depth);
                    case '[': return ReadArray(depth);
                    case '"': return ReadString();
                    case 't': Expect("true"); return true;
                    case 'f': Expect("false"); return false;
                    case 'n': Expect("null"); return null;
                    default:
                        if (c == '-' || (c >= '0' && c <= '9')) return ReadNumber();
                        throw new JsonException("unexpected '" + c + "' at " + i);
                }
            }

            void Expect(string word)
            {
                if (string.CompareOrdinal(s, i, word, 0, word.Length) != 0) throw new JsonException("expected " + word + " at " + i);
                i += word.Length;
            }

            Dictionary<string, object> ReadObject(int depth)
            {
                var obj = new Dictionary<string, object>();
                i++; // {
                SkipWs();
                if (Peek() == '}') { i++; return obj; }
                while (true)
                {
                    SkipWs();
                    if (Peek() != '"') throw new JsonException("expected key at " + i);
                    var key = ReadString();
                    SkipWs();
                    if (Peek() != ':') throw new JsonException("expected ':' at " + i);
                    i++;
                    SkipWs();
                    obj[key] = ReadValue(depth + 1);
                    SkipWs();
                    var c = Peek();
                    i++;
                    if (c == '}') return obj;
                    if (c != ',') throw new JsonException("expected ',' or '}' at " + (i - 1));
                }
            }

            List<object> ReadArray(int depth)
            {
                var list = new List<object>();
                i++; // [
                SkipWs();
                if (Peek() == ']') { i++; return list; }
                while (true)
                {
                    SkipWs();
                    list.Add(ReadValue(depth + 1));
                    SkipWs();
                    var c = Peek();
                    i++;
                    if (c == ']') return list;
                    if (c != ',') throw new JsonException("expected ',' or ']' at " + (i - 1));
                }
            }

            string ReadString()
            {
                i++; // "
                var sb = new StringBuilder();
                while (true)
                {
                    if (i >= s.Length) throw new JsonException("unterminated string");
                    var c = s[i++];
                    if (c == '"') return sb.ToString();
                    if (c < 0x20) throw new JsonException("control character in string");
                    if (c != '\\')
                    {
                        sb.Append(c);
                        continue;
                    }
                    if (i >= s.Length) throw new JsonException("unterminated escape");
                    var e = s[i++];
                    switch (e)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (i + 4 > s.Length) throw new JsonException("short \\u escape");
                            int code;
                            if (!int.TryParse(s.Substring(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out code))
                                throw new JsonException("bad \\u escape");
                            sb.Append((char)code);
                            i += 4;
                            break;
                        default:
                            throw new JsonException("bad escape \\" + e);
                    }
                }
            }

            object ReadNumber()
            {
                var start = i;
                if (s[i] == '-') i++;
                while (i < s.Length && "0123456789.eE+-".IndexOf(s[i]) >= 0) i++;
                var text = s.Substring(start, i - start);
                double d;
                if (!double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out d))
                    throw new JsonException("bad number '" + text + "'");
                return d;
            }
        }

        // ---------------- Lesehilfen für Nachrichten ----------------

        public static string Str(IDictionary<string, object> obj, string key, string fallback = "")
        {
            object v;
            if (obj == null || !obj.TryGetValue(key, out v) || v == null) return fallback;
            if (v is string s) return s;
            if (v is double d) return d.ToString("R", CultureInfo.InvariantCulture);
            if (v is bool b) return b ? "true" : "false";
            return fallback;
        }

        public static double Num(IDictionary<string, object> obj, string key, double fallback)
        {
            object v;
            if (obj == null || !obj.TryGetValue(key, out v) || v == null) return fallback;
            if (v is double d) return double.IsNaN(d) ? fallback : d;
            if (v is bool b) return b ? 1 : 0;
            if (v is string s)
            {
                double parsed;
                if (double.TryParse(s.Replace(',', '.'), NumberStyles.Float, CultureInfo.InvariantCulture, out parsed)) return parsed;
            }
            return fallback;
        }

        public static bool Bool(IDictionary<string, object> obj, string key, bool fallback)
        {
            object v;
            if (obj == null || !obj.TryGetValue(key, out v) || v == null) return fallback;
            if (v is bool b) return b;
            if (v is double d) return d != 0;
            if (v is string s)
            {
                s = s.Trim().ToLowerInvariant();
                if (s == "true" || s == "1" || s == "on" || s == "an" || s == "ja" || s == "yes") return true;
                if (s == "false" || s == "0" || s == "off" || s == "aus" || s == "nein" || s == "no") return false;
            }
            return fallback;
        }

        public static Dictionary<string, object> Obj(IDictionary<string, object> obj, string key)
        {
            object v;
            if (obj == null || !obj.TryGetValue(key, out v)) return new Dictionary<string, object>();
            return v as Dictionary<string, object> ?? new Dictionary<string, object>();
        }
    }
}
