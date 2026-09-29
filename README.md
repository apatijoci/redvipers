# Redvipers tabella – automatikus napi frissítés

Minden reggel lekéri az F csoport meccseit a bajnokság oldaláról
(kispalya.nyiregyhazisc.hu), és frissíti a tabellát egy saját linken,
amit bárki megnyithat fiók nélkül.

## Beállítás (egyszer, kb. 10 perc, gépről a legkényelmesebb)

1. **GitHub-fiók**: regisztrálj a github.com oldalon, ha még nincs fiókod.
2. **Új repó**: jobb felül „+” → *New repository*.
   Név: `redvipers`, legyen **Public**, majd *Create repository*.
3. **Fájlok feltöltése**: a repó oldalán *uploading an existing file* link
   (vagy *Add file → Upload files*). Húzd be ezeket:
   `scrape.py`, `template.html`, `README.md` és a `docs` mappát
   (benne az `index.html`-lel). Lent *Commit changes*.
4. **Az időzítő fájl**: *Add file → Create new file*.
   Fájlnévnek írd be pontosan: `.github/workflows/update.yml`
   (a perjelektől mappák lesznek), és másold bele az `update.yml`
   tartalmát. *Commit changes*.
5. **Weboldal bekapcsolása**: *Settings → Pages*.
   Source: *Deploy from a branch*, Branch: `main`, mappa: `/docs` → *Save*.
   1–2 perc múlva megjelenik a link: `https://<felhasználóneved>.github.io/redvipers/`
6. **Első futtatás kipróbálása**: *Actions* fül → bal oldalt
   *Tabella frissítése* → *Run workflow*. Ha zöld pipát kapsz, kész.

Innentől minden reggel (nyári időben 6-kor, téliben 5-kor) magától frissül.
Ezt a linket tedd ki a Messenger-csoportba.

## Ha valami nem működik

- **Piros X az Actions fülön, „Permission denied” / 403 hiba**:
  *Settings → Actions → General → Workflow permissions* →
  *Read and write permissions* → *Save*, majd futtasd újra.
- **„gyanúsan kevés adat” hiba**: a bajnokság oldala megváltozhatott.
  Ilyenkor a régi, jó tabella marad kint, semmi nem romlik el.
  Küldd el a hibaüzenetet Claude-nak, és kijavítja a scriptet.
- **Új szezon / más csoport**: a `scrape.py` elején az `URL`,
  `OUR_TEAM` és `VENUE` sort kell átírni.
- **Többször is frissítsen naponta?** Az `update.yml`-ben a `cron` sor
  alá tehetsz még egyet, pl. `- cron: "0 20 * * *"` (este 10, nyári időben).
