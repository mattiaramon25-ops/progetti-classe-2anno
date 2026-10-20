const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { ClientLM, ErroreLM, configurazione, elencoModelli, leggiEnv, soloModelliChat } = require("../src/lm-api");
const { FintoLMStudio } = require("./finto-lm");

let finto;
let client;

beforeEach(async () => {
  finto = new FintoLMStudio();
  client = new ClientLM(await finto.avvia());
});

afterEach(() => finto.chiudi());

// Scrive un file .env temporaneo e ne restituisce il percorso
function fileEnv(contenuto) {
  const cartella = fs.mkdtempSync(path.join(os.tmpdir(), "lm-chat-"));
  const percorso = path.join(cartella, ".env");
  fs.writeFileSync(percorso, contenuto, "utf-8");
  return percorso;
}

// Raccoglie tutti i pezzi dello streaming in una lista
async function tuttiIPezzi(generatore) {
  const pezzi = [];
  for await (const pezzo of generatore) pezzi.push(pezzo);
  return pezzi;
}

// --- Configurazione (.env) ---

test("leggiEnv legge le coppie e salta commenti, righe vuote e virgolette", () => {
  const percorso = fileEnv('# commento\n\nLM_BASE_URL = "http://pc:1234"\nLM_MODEL=\'qwen\'\nriga senza uguale\n');
  assert.deepEqual(leggiEnv(percorso), { LM_BASE_URL: "http://pc:1234", LM_MODEL: "qwen" });
});

test("leggiEnv con il file mancante restituisce un oggetto vuoto", () => {
  assert.deepEqual(leggiEnv(path.join(os.tmpdir(), "non-esiste", ".env")), {});
});

test("configurazione usa il .env e toglie la barra finale dall'indirizzo", () => {
  const percorso = fileEnv("LM_BASE_URL=http://pc:1234/\nLM_MODEL=qwen\n");
  assert.deepEqual(configurazione(percorso, {}), { baseUrl: "http://pc:1234", modello: "qwen" });
});

test("configurazione: le variabili di ambiente vincono sul .env", () => {
  const percorso = fileEnv("LM_BASE_URL=http://pc:1234\nLM_MODEL=qwen\n");
  const ambiente = { LM_BASE_URL: "http://altro:5678", LM_MODEL: "gemma" };
  assert.deepEqual(configurazione(percorso, ambiente), { baseUrl: "http://altro:5678", modello: "gemma" });
});

test("configurazione senza valori usa localhost:1234 e nessun modello", () => {
  const percorso = fileEnv("");
  assert.deepEqual(configurazione(percorso, {}), { baseUrl: "http://localhost:1234", modello: null });
});

test("soloModelliChat toglie i modelli di embedding", () => {
  const nomi = ["qwen", "text-embedding-nomic", "Nomic-EMBED", "gemma"];
  assert.deepEqual(soloModelliChat(nomi), ["qwen", "gemma"]);
});

test("elencoModelli toglie gli embedding e sceglie il primo modello", () => {
  assert.deepEqual(elencoModelli(["qwen", "text-embedding-x", "gemma"], null), {
    modelli: ["qwen", "gemma"],
    scelto: "qwen",
  });
});

test("elencoModelli sceglie il modello del .env anche se non è caricato", () => {
  // LM Studio può caricarlo da solo al primo messaggio
  assert.deepEqual(elencoModelli(["qwen"], "gemma"), { modelli: ["gemma", "qwen"], scelto: "gemma" });
  assert.deepEqual(elencoModelli(["qwen", "gemma"], "gemma"), { modelli: ["qwen", "gemma"], scelto: "gemma" });
});

test("elencoModelli senza modelli da chat dà un ErroreLM", () => {
  assert.throws(() => elencoModelli(["text-embedding-x"], null), {
    name: "ErroreLM",
    message: "Nessun modello caricato in LM Studio: caricane uno e premi Riprova.",
  });
});

// --- Modelli ---

test("modelli restituisce i nomi dei modelli caricati", async () => {
  assert.deepEqual(await client.modelli(), ["modello-a", "modello-b"]);
});

test("se LM Studio è spento l'errore spiega cosa controllare", async () => {
  await finto.chiudi();
  await assert.rejects(client.modelli(), (errore) => {
    assert.ok(errore instanceof ErroreLM);
    assert.match(errore.message, /Impossibile contattare LM Studio su http:\/\/127\.0\.0\.1:\d+/);
    return true;
  });
});

test("un errore HTTP diventa un ErroreLM con il codice", async () => {
  finto.statoHttp = 500;
  await assert.rejects(client.modelli(), { name: "ErroreLM", message: /errore 500/ });
});

test("una risposta che non è JSON diventa un ErroreLM", async () => {
  finto.corpoNonValido = true;
  await assert.rejects(client.modelli(), { name: "ErroreLM", message: "Risposta non valida da LM Studio." });
});

// --- Risposta tutta insieme (come client1) ---

test("chiedi invia modello e messaggi e restituisce la risposta senza spazi ai lati", async () => {
  const messaggi = [{ role: "user", content: "Ciao" }];
  assert.equal(await client.chiedi("modello-a", messaggi), "Ciao!");
  assert.deepEqual(finto.richieste, [{ model: "modello-a", messages: messaggi, stream: false }]);
});

test("chiedi con una risposta senza 'choices' dà un ErroreLM", async () => {
  finto.risposta = undefined; // il JSON diventa {"choices":[{"message":{}}]}
  await assert.rejects(client.chiedi("modello-a", []), { name: "ErroreLM" });
});

// --- Streaming (come client2) ---

test("chiediStream restituisce i pezzi uno alla volta e si ferma a [DONE]", async () => {
  const messaggi = [{ role: "user", content: "Ciao" }];
  assert.deepEqual(await tuttiIPezzi(client.chiediStream("modello-a", messaggi)), ["Ci", "ao", "!"]);
  assert.equal(finto.richieste[0].stream, true);
});

test("chiediStream con un errore HTTP dà un ErroreLM", async () => {
  finto.statoHttp = 404;
  await assert.rejects(tuttiIPezzi(client.chiediStream("x", [])), { name: "ErroreLM", message: /errore 404/ });
});

test("chiediStream si ferma in silenzio quando si preme Stop", async () => {
  finto.pezzi = ["uno", "due", "tre", "quattro"];
  finto.ritardoPezzi = 50;
  const stop = new AbortController();
  const pezzi = [];
  for await (const pezzo of client.chiediStream("x", [], stop.signal)) {
    pezzi.push(pezzo);
    stop.abort(); // Stop subito dopo il primo pezzo
  }
  assert.deepEqual(pezzi, ["uno"]);
});
