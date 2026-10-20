// Preferenze dell'interfaccia salvate in un piccolo file JSON.
//
// Il file (impostazioni_gui.json) è escluso da git: ognuno ha le sue.
// Se manca o è rovinato si usano i valori predefiniti, senza errori.

const fs = require("node:fs");

const PREDEFINITE = {
  tema: null, // null = come Windows, altrimenti "light" o "dark"
  barra_aperta: true,
  streaming: true,
  memoria: false,
};
const TEMI = [null, "light", "dark"];

// Legge le preferenze; i valori mancanti o non validi diventano quelli predefiniti
function carica(percorso) {
  const valori = { ...PREDEFINITE };
  let letti;
  try {
    letti = JSON.parse(fs.readFileSync(percorso, "utf-8"));
  } catch {
    return valori;
  }
  if (typeof letti !== "object" || letti === null) return valori;
  if (TEMI.includes(letti.tema)) valori.tema = letti.tema;
  for (const chiave of ["barra_aperta", "streaming", "memoria"]) {
    if (typeof letti[chiave] === "boolean") valori[chiave] = letti[chiave];
  }
  return valori;
}

// Scrive le preferenze. Se non ci riesce pazienza: l'app funziona lo stesso.
function salva(percorso, valori) {
  try {
    fs.writeFileSync(percorso, JSON.stringify(valori, null, 2), "utf-8");
  } catch {
    // niente da fare
  }
}

module.exports = { PREDEFINITE, carica, salva };
