/**
 * Salecta labels → Google Sheet
 *
 * Paste this whole file into Extensions → Apps Script in a new Google Sheet,
 * then Deploy → New deployment → Web app (Execute as: Me; Who has access:
 * Anyone). Put the web app URL into annotate/index.html (the
 * salecta-sheet-url meta tag).
 *
 * Each answer becomes one row in the "labels" tab. If an annotator goes back
 * and changes an answer, the same row is updated instead of adding a new one
 * (keyed on session_id + item_id).
 */

const TAB = 'labels';
const HEAD = ['received_at', 'annotator', 'session_id', 'dataset_fp', 'sample_pct',
              'item_id', 'decision', 'natural', 'meaning', 'comment', 'text', 'labelled_at'];
const ALLOWED_DECISIONS = ['COMPLY', 'REFUSE', 'UNSURE'];
const ALLOWED_NATURAL = ['yes', 'somewhat', 'no'];

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(TAB);
  if (!sh) {
    sh = ss.insertSheet(TAB);
    sh.appendRow(HEAD);
    sh.setFrozenRows(1);
  }
  return sh;
}

// Trim, cap length, and stop text being read as a spreadsheet formula.
function clean_(v, max) {
  let s = String(v == null ? '' : v).slice(0, max);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return out_({ ok: true, service: 'salecta-labels' });
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.tool !== 'salecta-annotate') return out_({ ok: false, error: 'unknown sender' });
    const session = clean_(body.session_id, 64);
    if (!session) return out_({ ok: false, error: 'missing session_id' });

    const sh = sheet_();
    const values = sh.getDataRange().getValues();
    const rowOf = {};
    for (let i = 1; i < values.length; i++) rowOf[values[i][2] + '|' + values[i][5]] = i + 1;

    let saved = 0;
    (body.labels || []).slice(0, 200).forEach(function (l) {
      if (ALLOWED_DECISIONS.indexOf(l.decision) < 0 || ALLOWED_NATURAL.indexOf(l.natural) < 0) return;
      const row = [new Date(), clean_(body.annotator, 60), session, clean_(body.dataset_fp, 40),
                   Number(body.sample_pct) || '', clean_(l.item_id, 10), l.decision, l.natural,
                   clean_(l.meaning, 1000), clean_(l.comment, 1000), clean_(l.text, 500), clean_(l.ts, 40)];
      const key = session + '|' + row[5];
      if (rowOf[key]) {
        sh.getRange(rowOf[key], 1, 1, row.length).setValues([row]);
      } else {
        sh.appendRow(row);
        rowOf[key] = sh.getLastRow();
      }
      saved++;
    });
    return out_({ ok: true, saved: saved });
  } catch (err) {
    return out_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}
