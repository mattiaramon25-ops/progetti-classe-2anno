// Ponte tra la pagina e il processo principale (main.js).
//
// Per sicurezza la pagina non può usare Node.js né fare richieste di rete da
// sola: può solo chiamare le funzioni qui sotto, disponibili come window.lm.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("lm", {
  // { preferenze }
  avvio: () => ipcRenderer.invoke("avvio"),
  // { modelli, scelto } oppure { errore }
  modelli: () => ipcRenderer.invoke("modelli"),
  // { risposta } oppure { errore }
  chiedi: (id, modello, messaggi, streaming) =>
    ipcRenderer.invoke("chiedi", id, modello, messaggi, streaming),
  ferma: (id) => ipcRenderer.send("ferma", id),
  // Chiama funzione(id, pezzo) per ogni pezzo di testo dello streaming
  quandoArrivaUnPezzo: (funzione) =>
    ipcRenderer.on("pezzo", (_evento, id, pezzo) => funzione(id, pezzo)),
  salvaPreferenze: (preferenze) => ipcRenderer.send("salva-preferenze", preferenze),
});
