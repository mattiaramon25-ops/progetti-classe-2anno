const { test } = require("node:test");
const assert = require("node:assert/strict");

const {
  LIMITE_IMMAGINE,
  LIMITE_TESTO,
  ErroreAllegato,
  leggiAllegato,
  componiContenuto,
  testoDelContenuto,
  blocchiDiCodice,
  nomeFileCodice,
  bytesDaDataUrl,
} = require("../renderer/allegati");

const byte = (testo) => new TextEncoder().encode(testo);
// Un PNG di 1×1 pixel: bastano i primi byte per riconoscerlo
const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13]);

// --- Lettura degli allegati ---

test("un'immagine diventa un data URL in base64", () => {
  const allegato = leggiAllegato("foto.png", "image/png", PNG);
  assert.equal(allegato.tipo, "immagine");
  assert.equal(allegato.nome, "foto.png");
  assert.equal(allegato.dataUrl, `data:image/png;base64,${Buffer.from(PNG).toString("base64")}`);
});

test("un file di testo viene letto come testo, qualunque sia l'estensione", () => {
  const allegato = leggiAllegato("script.py", "", byte("print('ciao')\n"));
  assert.deepEqual(allegato, { tipo: "testo", nome: "script.py", testo: "print('ciao')\n" });
});

test("le lettere accentate in UTF-8 restano intatte", () => {
  assert.equal(leggiAllegato("note.txt", "text/plain", byte("perché è così")).testo, "perché è così");
});

test("un file binario (es. PDF o docx) non è supportato", () => {
  const binario = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x00, 0xff, 0xfe]);
  assert.throws(() => leggiAllegato("documento.pdf", "application/pdf", binario), ErroreAllegato);
});

test("un'immagine in un formato non supportato dà un errore chiaro", () => {
  assert.throws(() => leggiAllegato("foto.tiff", "image/tiff", PNG), /formato/i);
});

test("un'immagine troppo grande viene rifiutata", () => {
  const grande = new Uint8Array(LIMITE_IMMAGINE + 1);
  assert.throws(() => leggiAllegato("grande.png", "image/png", grande), /troppo grande/i);
});

test("un file di testo troppo grande viene rifiutato", () => {
  const grande = new Uint8Array(LIMITE_TESTO + 1).fill(97); // tutte "a"
  assert.throws(() => leggiAllegato("grande.txt", "text/plain", grande), /troppo grande/i);
});

// --- Messaggio da mandare al modello ---

test("senza allegati il contenuto resta una semplice stringa", () => {
  assert.equal(componiContenuto("ciao", []), "ciao");
});

test("i file di testo vengono aggiunti alla domanda, con il loro nome", () => {
  const file = { tipo: "testo", nome: "a.py", testo: "x = 1" };
  const contenuto = componiContenuto("Cosa fa?", [file]);
  assert.equal(typeof contenuto, "string");
  assert.match(contenuto, /^Cosa fa\?/);
  assert.match(contenuto, /File "a\.py":\n```\nx = 1\n```/);
});

test("con le immagini il contenuto diventa una lista di parti (formato OpenAI)", () => {
  const immagine = { tipo: "immagine", nome: "f.png", dataUrl: "data:image/png;base64,AAAA" };
  assert.deepEqual(componiContenuto("Descrivi", [immagine]), [
    { type: "text", text: "Descrivi" },
    { type: "image_url", image_url: { url: "data:image/png;base64,AAAA" } },
  ]);
});

test("solo un'immagine, senza testo: niente parte di testo vuota", () => {
  const immagine = { tipo: "immagine", nome: "f.png", dataUrl: "data:image/png;base64,AAAA" };
  assert.deepEqual(componiContenuto("", [immagine]), [
    { type: "image_url", image_url: { url: "data:image/png;base64,AAAA" } },
  ]);
});

test("testoDelContenuto ricava il testo sia da una stringa sia da una lista di parti", () => {
  assert.equal(testoDelContenuto("ciao"), "ciao");
  assert.equal(
    testoDelContenuto([{ type: "text", text: "ciao" }, { type: "image_url", image_url: { url: "x" } }]),
    "ciao"
  );
});

// --- Download del codice scritto dal modello ---

test("blocchiDiCodice trova i blocchi ``` con il loro linguaggio", () => {
  const risposta = "Ecco:\n```python\nprint(1)\n```\ne poi\n```\nciao\n```\n";
  assert.deepEqual(blocchiDiCodice(risposta), [
    { linguaggio: "python", codice: "print(1)\n" },
    { linguaggio: "", codice: "ciao\n" },
  ]);
});

test("blocchiDiCodice senza blocchi restituisce una lista vuota", () => {
  assert.deepEqual(blocchiDiCodice("solo testo"), []);
});

test("blocchiDiCodice ignora un blocco non ancora chiuso", () => {
  assert.deepEqual(blocchiDiCodice("```js\nlet a = 1;"), []);
});

test("nomeFileCodice sceglie l'estensione giusta dal linguaggio", () => {
  assert.equal(nomeFileCodice("python", 1), "codice-1.py");
  assert.equal(nomeFileCodice("JavaScript", 2), "codice-2.js");
  assert.equal(nomeFileCodice("html", 3), "codice-3.html");
  assert.equal(nomeFileCodice("", 4), "codice-4.txt");
  assert.equal(nomeFileCodice("linguaggio-strano", 5), "codice-5.txt");
  assert.equal(nomeFileCodice("constructor", 6), "codice-6.txt");
});

test("bytesDaDataUrl ricostruisce i byte originali di un'immagine", () => {
  const dataUrl = `data:image/png;base64,${Buffer.from(PNG).toString("base64")}`;
  assert.deepEqual(bytesDaDataUrl(dataUrl), PNG);
});
