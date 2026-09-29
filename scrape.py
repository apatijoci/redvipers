#!/usr/bin/env python3
"""Lekéri a Nyíregyházi kispályás bajnokság F csoportjának meccseit,
és legyártja a docs/index.html oldalt (tabella, meccsek, összesítő)."""
import json, re, sys, html
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from urllib.request import Request, urlopen

URL = "https://kispalya.nyiregyhazisc.hu/eredmenyek/6"   # F csoport
OUR_TEAM = "REDVIPERS"
VENUE = "Városi Stadion, műfüves pályák"


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


def main():
    page = fetch(URL)
    matches = parse(page)
    played = [m for m in matches if m["hg"] is not None]
    ours = [m for m in matches if OUR_TEAM in (m["home"], m["away"])]
    # Biztonsági fék: ha az oldal szerkezete megváltozott, ne írjuk felül a jó adatot üressel.
    if len(matches) < 12 or not ours or not played:
        sys.exit(f"Hiba: gyanúsan kevés adat ({len(matches)} meccs, {len(ours)} saját). Nem frissítem az oldalt.")

    now = datetime.now(timezone(timedelta(hours=2)))  # közelítő magyar idő a kijelzéshez
    state = {
        "our": OUR_TEAM,
        "venue": VENUE,
        "source": URL,
        "fetched": now.strftime("%Y-%m-%d %H:%M"),
        "matches": matches,
    }
    tpl = open("template.html", encoding="utf-8").read()
    data = json.dumps(state, ensure_ascii=False).replace("<", "\\u003c")
    open("docs/index.html", "w", encoding="utf-8").write(tpl.replace("__STATE__", data))
    print(f"OK: {len(matches)} meccs, ebből {len(played)} lejátszott, {len(ours)} Redvipers-meccs.")


if __name__ == "__main__":
    main()
