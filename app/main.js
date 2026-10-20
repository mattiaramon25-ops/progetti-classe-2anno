// Processo principale di Electron: apre la finestra e parla con LM Studio.
//
// La pagina (cartella renderer/) si occupa solo della grafica: quando serve
// qualcosa a LM Studio lo chiede a questo file tramite IPC (messaggi tra
// la pagina e il processo principale), passando per preload.js.
//
// Avvio (dalla cartella app/):
//     npm start

const path = require("node:path");
const { app, BrowserWindow, Menu, ipcMain, nativeTheme } = require("electron");

const impostazioni = require("./src/impostazioni");
const { ClientLM, ErroreLM, configurazione, elencoModelli } = require("./src/lm-api");

// Il .env e le preferenze stanno nella cartella principale del progetto,
// insieme ai client della lezione 1
const ROOT = path.join(__dirname, "..");
const PERCORSO_IMPOSTAZIONI = path.join(ROOT, "impostazioni_gui.json");

const { baseUrl, modello: modelloPreferito } = configurazione(path.join(ROOT, ".env"));
const client = new ClientLM(baseUrl);

// Richieste in corso: id → AbortController, per poterle fermare con Stop
const richiesteInCorso = new Map();

// Messaggio da mostrare all'utente: gli ErroreLM sono già scritti per lui
function testoErrore(errore) {
  return errore instanceof ErroreLM ? errore.message : `Errore inatteso: ${errore.message}`;
}

// --- Richieste dalla pagina ---

ipcMain.handle("avvio", () => ({
  preferenze: impostazioni.carica(PERCORSO_IMPOSTAZIONI),
}));

ipcMain.handle("modelli", async () => {
  try {
    return elencoModelli(await client.modelli(), modelloPreferito);
  } catch (errore) {
    return { errore: testoErrore(errore) };
  }
});

// Una domanda al modello. Restituisce { risposta } oppure { errore }.
// Con lo streaming (come client2) ogni pezzo viene mandato subito alla
// pagina con il messaggio "pezzo"; senza (come client1) arriva tutto alla fine.
ipcMain.handle("chiedi", async (evento, id, modello, messaggi, streaming) => {
  const stop = new AbortController();
  richiesteInCorso.set(id, stop);
  try {
    if (!streaming) return { risposta: await client.chiedi(modello, messaggi) };
    let risposta = "";
    for await (const pezzo of client.chiediStream(modello, messaggi, stop.signal)) {
      risposta += pezzo;
      evento.sender.send("pezzo", id, pezzo);
    }
    return { risposta: risposta.trim() };
  } catch (errore) {
    return { errore: testoErrore(errore) };
  } finally {
    richiesteInCorso.delete(id);
  }
});

ipcMain.on("ferma", (_evento, id) => {
  richiesteInCorso.get(id)?.abort();
});

ipcMain.on("salva-preferenze", (_evento, preferenze) => {
  // "system" = come Windows. Cambiando il tema qui cambiano sia la barra
  // del titolo sia i colori della pagina (vedi @media in stile.css).
  nativeTheme.themeSource = preferenze.tema ?? "system";
  impostazioni.salva(PERCORSO_IMPOSTAZIONI, preferenze);
});

// --- Finestra ---

function creaFinestra() {
  nativeTheme.themeSource = impostazioni.carica(PERCORSO_IMPOSTAZIONI).tema ?? "system";

  const finestra = new BrowserWindow({
    width: 1040,
    height: 700,
    minWidth: 760,
    minHeight: 600,
    title: "LM Chat",
    // Stesso colore dello sfondo della pagina: niente lampo bianco all'avvio
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#0E1129" : "#F1F8F3",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      // contextIsolation e sandbox sono già attivi di default: la pagina
      // non può usare Node.js, solo le funzioni messe a disposizione da preload.js
    },
  });
  finestra.once("ready-to-show", () => finestra.show());
  finestra.loadFile(path.join(__dirname, "renderer", "index.html"));
}

Menu.setApplicationMenu(null); // niente barra dei menu: l'app ha già i suoi pulsanti
app.whenReady().then(creaFinestra);
app.on("window-all-closed", () => app.quit());
