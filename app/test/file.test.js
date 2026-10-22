const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { nomeFileSicuro, scriviFile } = require("../src/file");

test("nomeFileSicuro lascia stare un nome normale", () => {
  assert.equal(nomeFileSicuro("foto vacanze.png"), "foto vacanze.png");
});

test("nomeFileSicuro toglie le cartelle: il file finisce dove sceglie l'utente", () => {
  assert.equal(nomeFileSicuro("../../Windows/system.ini"), "system.ini");
  assert.equal(nomeFileSicuro("C:\\Users\\a\\b.txt"), "b.txt");
});

test("nomeFileSicuro sostituisce i caratteri vietati da Windows", () => {
  assert.equal(nomeFileSicuro('a<b>c:d"e|f?g*.txt'), "a_b_c_d_e_f_g_.txt");
});

test("nomeFileSicuro con un nome vuoto o fatto solo di punti usa 'file'", () => {
  assert.equal(nomeFileSicuro(""), "file");
  assert.equal(nomeFileSicuro(".."), "file");
  assert.equal(nomeFileSicuro(undefined), "file");
});

test("scriviFile salva sia testo sia byte", async () => {
  const cartella = fs.mkdtempSync(path.join(os.tmpdir(), "lm-chat-"));
  const testo = path.join(cartella, "a.txt");
  const binario = path.join(cartella, "b.bin");
  await scriviFile(testo, "perché");
  await scriviFile(binario, new Uint8Array([0, 1, 255]));
  assert.equal(fs.readFileSync(testo, "utf-8"), "perché");
  assert.deepEqual([...fs.readFileSync(binario)], [0, 1, 255]);
});

test("scriviFile rifiuta un contenuto che non è né testo né byte", async () => {
  const percorso = path.join(os.tmpdir(), "non-scritto.txt");
  await assert.rejects(() => scriviFile(percorso, { a: 1 }), TypeError);
});
