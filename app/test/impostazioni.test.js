const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { PREDEFINITE, carica, salva } = require("../src/impostazioni");

function percorsoTemporaneo() {
  const cartella = fs.mkdtempSync(path.join(os.tmpdir(), "lm-chat-"));
  return path.join(cartella, "impostazioni_gui.json");
}

test("senza file si usano le preferenze predefinite", () => {
  assert.deepEqual(carica(percorsoTemporaneo()), PREDEFINITE);
});

test("un file rovinato non dà errori: valori predefiniti", () => {
  const percorso = percorsoTemporaneo();
  fs.writeFileSync(percorso, "{ non è json");
  assert.deepEqual(carica(percorso), PREDEFINITE);
});

test("i valori non validi vengono ignorati, quelli validi tenuti", () => {
  const percorso = percorsoTemporaneo();
  fs.writeFileSync(percorso, JSON.stringify({ tema: "viola", streaming: "sì", memoria: true }));
  assert.deepEqual(carica(percorso), { ...PREDEFINITE, memoria: true });
});

test("salva e poi carica restituisce le stesse preferenze", () => {
  const percorso = percorsoTemporaneo();
  const valori = { tema: "dark", barra_aperta: false, streaming: false, memoria: true };
  salva(percorso, valori);
  assert.deepEqual(carica(percorso), valori);
});

test("salva in una cartella che non esiste non lancia errori", () => {
  assert.doesNotThrow(() => salva(path.join(os.tmpdir(), "non-esiste", "x", "p.json"), PREDEFINITE));
});
