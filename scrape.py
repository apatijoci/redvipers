#!/usr/bin/env python3
"""Lekéri a Nyíregyházi kispályás bajnokság F csoportjának meccseit,
és legyártja a docs/index.html oldalt (tabella, meccsek, összesítő)."""
import json, os, re, sys, html
from datetime import datetime
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from urllib.request import Request, urlopen

URL = "https://kispalya.nyiregyhazisc.hu/eredmenyek/6"   # F csoport
OUR_TEAM = "REDVIPERS"
VENUE = "Városi Stadion, műfüves pályák"
MANUAL = "manual.json"   # kézzel beírt, még nem hivatalos eredmények
TZ = ZoneInfo("Europe/Budapest")


class Rows(HTMLParser):
    """Kigyűjti a táblázatsorokat cellák listájaként."""
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None
    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.rows.append(self.row)
            self.row = None
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Redvipers tabella)"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def parse(page):
    p = Rows()
    p.feed(page)
    matches, rnd = [], None
    re_round = re.compile(r"(\d+)\.\s*FORDUL", re.I)
    re_date = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})$")
    re_res = re.compile(r"^(\d+)\s*:\s*(\d+)$")
    for row in p.rows:
        cells = [html.unescape(c) for c in row]
        joined = " ".join(cells)
        m = re_round.search(cells[0]) if cells else None
        if m and len([c for c in cells if c]) == 1:
            rnd = int(m.group(1))
            continue
        if rnd is None or len(cells) < 5:
            continue
        dt_cell, pitch, home, away, res = cells[:5]
        if not (re_date.match(dt_cell) or "NINCS" in dt_cell.upper()):
            continue
        r = re_res.match(res)
        matches.append({
            "round": rnd,
            "dt": dt_cell if re_date.match(dt_cell) else "",
            "pitch": pitch,
            "home": home,
            "away": away,
            "hg": int(r.group(1)) if r else None,
            "ag": int(r.group(2)) if r else None,
        })
    return matches


def key(m):
    return (m["round"], m["home"], m["away"])


def load_manual():
    try:
        with open(MANUAL, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def add_manual(matches, manual, result, rnd, now):
    """Kézi eredmény felvétele a Redvipers szemszögéből ("MI:ŐK")."""
    r = re.match(r"^\s*(\d+)\s*[:\-–]\s*(\d+)\s*$", result)
    if not r:
        sys.exit(f"Hiba: az eredményt MI:ŐK formában add meg (pl. 5:3), ezt kaptam: {result!r}")
    us, them = int(r.group(1)), int(r.group(2))
    open_ours = [m for m in matches if OUR_TEAM in (m["home"], m["away"]) and m["hg"] is None]
    if rnd.strip():
        if not rnd.strip().isdigit():
            sys.exit(f"Hiba: a forduló egy szám legyen, ezt kaptam: {rnd!r}")
        cands = [m for m in open_ours if m["round"] == int(rnd)]
    else:
        # a legutóbbi, már elkezdődött meccsünk, aminek még nincs hivatalos eredménye
        started = [m for m in open_ours if m["dt"] and m["dt"] <= now.strftime("%Y-%m-%d %H:%M")]
        cands = sorted(started, key=lambda m: m["dt"])[-1:]
    if not cands:
        sys.exit("Hiba: nem találtam hozzá meccset (vagy már van hivatalos eredménye). "
                 "Add meg a forduló számát is.")
    m = cands[0]
    hg, ag = (us, them) if m["home"] == OUR_TEAM else (them, us)
    manual[:] = [e for e in manual if key(e) != key(m)]
    manual.append({"round": m["round"], "home": m["home"], "away": m["away"],
                   "hg": hg, "ag": ag, "added": now.strftime("%Y-%m-%d %H:%M")})
    print(f"Kézi eredmény felvéve: {m['round']}. forduló, {m['home']} {hg}:{ag} {m['away']}")


def apply_manual(matches, manual):
    """A kézi eredményeket beírja a meccsekbe, ahol még nincs hivatalos.
    Ha már van hivatalos, az nyer, és a kézi bejegyzés törlődik. Visszaadja a megtartandókat."""
    by_key = {key(m): m for m in matches}
    keep = []
    for e in manual:
        m = by_key.get(key(e))
        if m is None:
            print(f"Figyelem: a kézi bejegyzést nem találom az oldalon, megtartom: {e}")
            keep.append(e)
        elif m["hg"] is not None:
            diff = "" if (m["hg"], m["ag"]) == (e["hg"], e["ag"]) else f" – ELTÉRT a kézitől ({e['hg']}:{e['ag']})"
            print(f"Megjött a hivatalos eredmény: {m['home']} {m['hg']}:{m['ag']} {m['away']}{diff}. Kézi bejegyzés törölve.")
        else:
            m["hg"], m["ag"], m["manual"] = e["hg"], e["ag"], True
            keep.append(e)
    return keep


def main():
    page = fetch(URL)
    matches = parse(page)
    now = datetime.now(TZ)
    manual = load_manual()
    if os.environ.get("EREDMENY", "").strip():
        add_manual(matches, manual, os.environ["EREDMENY"], os.environ.get("FORDULO", ""), now)
    manual = apply_manual(matches, manual)
    played = [m for m in matches if m["hg"] is not None]
    ours = [m for m in matches if OUR_TEAM in (m["home"], m["away"])]
    # Biztonsági fék: ha az oldal szerkezete megváltozott, ne írjuk felül a jó adatot üressel.
    if len(matches) < 12 or not ours or not played:
        sys.exit(f"Hiba: gyanúsan kevés adat ({len(matches)} meccs, {len(ours)} saját). Nem frissítem az oldalt.")

    state = {
        "our": OUR_TEAM,
        "venue": VENUE,
        "source": URL,
        "repo": os.environ.get("GITHUB_REPOSITORY", "apatijoci/redvipers"),
        "fetched": now.strftime("%Y-%m-%d %H:%M"),
        "matches": matches,
    }
    tpl = open("template.html", encoding="utf-8").read()
    data = json.dumps(state, ensure_ascii=False).replace("<", "\\u003c")
    open("docs/index.html", "w", encoding="utf-8").write(tpl.replace("__STATE__", data))
    with open(MANUAL, "w", encoding="utf-8") as f:
        json.dump(manual, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"OK: {len(matches)} meccs, ebből {len(played)} lejátszott, {len(ours)} Redvipers-meccs, {len(manual)} kézi eredmény.")


if __name__ == "__main__":
    main()
