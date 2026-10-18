"""Plätze für die Produktions-Seite: welches Item (oder welche Flüssigkeit) ein Platz zeigt.

Ein Platz ist entweder fest gewählt („item.iron-plate“) oder automatisch (leer): Dann zeigt er das
nächstmeistproduzierte Item, das kein anderer Platz zeigt. Geblättert wird alphabetisch nach dem
übersetzten Namen, damit die Reihenfolge nicht mit den Mengen springt. Nur Standardbibliothek.
"""


class ItemSlots:
    def __init__(self, count):
        self.count = count
        self.picks = [""] * count     # Schlüssel „item.<name>“ / „fluid.<name>“ oder "" = automatisch
        self.rates = {}               # Schlüssel → (Produktion/min, Verbrauch/min)
        self.order = []               # Schlüssel nach Produktion absteigend (wie vom Mod)
        self.labels = {}              # Schlüssel → übersetzter Name

    # ---------------- Daten ----------------

    def update(self, items, labels):
        """items: Liste aus items.json ({n, k, p, c}); labels: Schlüssel → Name aus labels.txt."""
        self.rates, self.order = {}, []
        for e in items:
            if not isinstance(e, dict) or e.get("k") not in ("item", "fluid") or not e.get("n"):
                continue
            key = f"{e['k']}.{e['n']}"
            if key in self.rates:
                continue
            self.rates[key] = (_num(e.get("p")), _num(e.get("c")))
            self.order.append(key)
        self.labels = dict(labels)

    def label(self, key):
        return self.labels.get(key) or key.split(".", 1)[-1]

    def rate(self, key):
        return self.rates.get(key, (0.0, 0.0))

    # ---------------- Auflösen ----------------

    def resolve(self):
        """Liste je Platz: (Schlüssel oder "", automatisch?)."""
        taken = {p for p in self.picks if p}
        auto = iter(k for k in self.order if k not in taken)
        out = []
        for pick in self.picks:
            if pick:
                out.append((pick, False))
            else:
                out.append((next(auto, ""), True))
        return out

    # ---------------- Auswahl ändern ----------------

    def _sorted(self, extra=""):
        keys = set(self.order)
        if extra:
            keys.add(extra)
        return sorted(keys, key=lambda k: (self.label(k).lower(), k))

    def step(self, slot, direction):
        """Nächstes (+1) oder voriges (−1) Item für einen Platz; liefert den neuen Schlüssel."""
        current = self.resolve()[slot][0]
        keys = self._sorted(current)
        if not keys:
            return ""
        i = keys.index(current) + direction if current in keys else (0 if direction > 0 else len(keys) - 1)
        self.picks[slot] = keys[i % len(keys)]
        return self.picks[slot]

    def set(self, slot, text):
        """Platz auf ein Item setzen: übersetzter oder interner Name (auch Teil davon, wenn eindeutig)."""
        low = text.strip().lower()
        keys = self._sorted()
        exact = [k for k in keys if low in (self.label(k).lower(), k.lower(), k.split(".", 1)[-1].lower())]
        hits = exact or [k for k in keys if low in self.label(k).lower() or low in k.lower()]
        if len(hits) != 1:
            return None, [self.label(k) for k in hits[:8]]
        self.picks[slot] = hits[0]
        return hits[0], []

    def auto(self, slot):
        self.picks[slot] = ""

    def all_auto(self):
        self.picks = [""] * self.count


def _num(v):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return 0.0
    return n if n == n and abs(n) < 1e15 else 0.0
