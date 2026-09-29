/**
 * Redvipers – ki jön a következő meccsre?
 * Google Táblázathoz kötött Apps Script: a weboldal ezen keresztül olvassa és írja a szavazatokat.
 *
 * Lapok (ha hiányoznak, maguktól létrejönnek):
 *   Névsor      – A oszlop: a játékosok neve (első sor fejléc). Ha üres, bárki beírhatja a nevét.
 *   Szavazatok  – meccs | név | válasz | időpont (ezt a script tölti)
 *
 * Közzététel: Telepítés (Deploy) → Új telepítés → Webes alkalmazás,
 *   Futtatás mint: Én, Hozzáférés: Bárki → a kapott /exec linket kell megadni.
 */

var STATUSES = ['jon', 'talan', 'nem'];

function sheets_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var roster = ss.getSheetByName('Névsor');
  if (!roster) {
    roster = ss.insertSheet('Névsor');
    roster.getRange(1, 1).setValue('Név').setFontWeight('bold');
  }
  var votes = ss.getSheetByName('Szavazatok');
  if (!votes) {
    votes = ss.insertSheet('Szavazatok');
    votes.getRange(1, 1, 1, 4).setValues([['Meccs', 'Név', 'Válasz', 'Időpont']]).setFontWeight('bold');
    votes.setFrozenRows(1);
  }
  return { roster: roster, votes: votes };
}

function roster_(sh) {
  var n = sh.getLastRow();
  if (n < 2) return [];
  return sh.getRange(2, 1, n - 1, 1).getValues()
    .map(function (r) { return String(r[0]).trim(); })
    .filter(function (s) { return s; });
}

function state_(match) {
  var s = sheets_();
  var votes = {};
  var n = s.votes.getLastRow();
  if (n >= 2 && match) {
    s.votes.getRange(2, 1, n - 1, 4).getValues().forEach(function (r) {
      if (String(r[0]) === match) votes[String(r[1])] = String(r[2]);
    });
  }
  return { ok: true, roster: roster_(s.roster), votes: votes };
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// GET ?match=...  → névsor + az adott meccs szavazatai
function doGet(e) {
  return json_(state_(String((e.parameter || {}).match || '')));
}

// POST {match, name, status}  → szavazat mentése / módosítása (status "" = visszavonás)
function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var d = JSON.parse(e.postData.contents);
    var match = String(d.match || '').slice(0, 200);
    var name = String(d.name || '').trim().slice(0, 40);
    var status = String(d.status || '');
    if (!match || !name) return json_({ ok: false, error: 'Hiányzó meccs vagy név.' });
    if (status && STATUSES.indexOf(status) < 0) return json_({ ok: false, error: 'Érvénytelen válasz.' });
    var s = sheets_();
    var roster = roster_(s.roster);
    if (roster.length && roster.indexOf(name) < 0) return json_({ ok: false, error: 'Ez a név nincs a névsorban.' });

    var n = s.votes.getLastRow();
    var rows = n >= 2 ? s.votes.getRange(2, 1, n - 1, 2).getValues() : [];
    var row = -1;
    for (var i = 0; i < rows.length; i++) {
      if (String(rows[i][0]) === match && String(rows[i][1]) === name) { row = i + 2; break; }
    }
    if (!status) {
      if (row > 0) s.votes.deleteRow(row);
    } else if (row > 0) {
      s.votes.getRange(row, 3, 1, 2).setValues([[status, new Date()]]);
    } else {
      s.votes.appendRow([match, name, status, new Date()]);
    }
    return json_(state_(match));
  } finally {
    lock.releaseLock();
  }
}

// Egyszer futtasd kézzel a szerkesztőből: létrehozza a lapokat és kéri az engedélyt.
function beallitas() {
  sheets_();
}
