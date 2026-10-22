// Salvataggio dei file scaricati dalla chat (immagini, allegati, risposte).
//
// La pagina non può scrivere sul disco: manda nome e contenuto a main.js,
// che chiede all'utente dove salvare e poi usa queste funzioni.

const fs = require("node:fs");

// Caratteri che Windows non accetta nei nomi dei file, più quelli di controllo
const CARATTERI_VIETATI = /[<>:"/\\|?*\u0000-\u001f]/g;

// Il nome arriva dalla pagina: si tiene solo il nome vero e proprio, senza
// cartelle, così il file finisce sempre nella cartella scelta dall'utente.
function nomeFileSicuro(nome) {
  const ultimo = String(nome ?? "").split(/[\\/]/).pop();
  const pulito = ultimo.replace(CARATTERI_VIETATI, "_").replace(/^[\s.]+|[\s.]+$/g, "");
  return pulito || "file";
}

// Scrive un testo (in UTF-8) oppure dei byte (Uint8Array)
async function scriviFile(percorso, contenuto) {
  if (typeof contenuto !== "string" && !(contenuto instanceof Uint8Array)) {
    throw new TypeError("Il contenuto deve essere un testo o dei byte.");
  }
  await fs.promises.writeFile(percorso, contenuto);
}

module.exports = { nomeFileSicuro, scriviFile };
