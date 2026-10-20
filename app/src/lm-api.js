// Logica per parlare con LM Studio, separata dalla grafica.
//
// Riprende il codice dei client della lezione 1 (lettura del .env, elenco dei
// modelli, risposta normale e in streaming) ma senza console.log né input,
// così l'interfaccia grafica può usarlo e i test possono verificarlo da soli.
//
// Usa solo Node.js, senza librerie esterne.

const fs = require("node:fs");

const URL_PREDEFINITO = "http://localhost:1234";

// Errore con un messaggio già comprensibile, da mostrare nella finestra
class ErroreLM extends Error {
  constructor(messaggio) {
    super(messaggio);
    this.name = "ErroreLM";
  }
}

// Legge un file .env (CHIAVE=valore) e restituisce le coppie trovate
function leggiEnv(percorso) {
  if (!fs.existsSync(percorso)) return {};
  const valori = {};
  for (let riga of fs.readFileSync(percorso, "utf-8").split(/\r?\n/)) {
    riga = riga.trim();
    if (!riga || riga.startsWith("#") || !riga.includes("=")) continue;
    const posizione = riga.indexOf("=");
    const chiave = riga.slice(0, posizione).trim();
    const valore = riga.slice(posizione + 1).trim().replace(/^["']|["']$/g, "");
    valori[chiave] = valore;
  }
  return valori;
}

// Restituisce { baseUrl, modello }. Come nei client della lezione 1,
// le variabili di ambiente già impostate hanno la precedenza sul file .env.
function configurazione(percorsoEnv, ambiente = process.env) {
  const valori = { ...leggiEnv(percorsoEnv), ...ambiente };
  const baseUrl = valori.LM_BASE_URL || URL_PREDEFINITO;
  return { baseUrl: baseUrl.replace(/\/+$/, ""), modello: valori.LM_MODEL || null };
}

// Toglie i modelli di embedding: trasformano il testo in numeri, non sanno chattare
function soloModelliChat(nomi) {
  return nomi.filter((nome) => !nome.toLowerCase().includes("embed"));
}

// Prepara il menu dei modelli: { modelli, scelto }.
// Il modello del .env viene scelto anche se non è caricato:
// LM Studio può caricarlo da solo al primo messaggio.
function elencoModelli(nomi, preferito) {
  const modelli = soloModelliChat(nomi);
  if (preferito && !modelli.includes(preferito)) modelli.unshift(preferito);
  if (modelli.length === 0) {
    throw new ErroreLM("Nessun modello caricato in LM Studio: caricane uno e premi Riprova.");
  }
  return { modelli, scelto: preferito || modelli[0] };
}

// Client per il server locale di LM Studio (API compatibile OpenAI)
class ClientLM {
  constructor(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  // Fa la richiesta HTTP e restituisce la risposta ancora da leggere.
  // Gli errori di rete diventano ErroreLM con un messaggio chiaro.
  async _apri(metodo, endpoint, dati, segnale) {
    let risposta;
    try {
      risposta = await fetch(`${this.baseUrl}/v1/${endpoint}`, {
        method: metodo,
        headers: { "Content-Type": "application/json" },
        body: dati === undefined ? undefined : JSON.stringify(dati),
        signal: segnale,
      });
    } catch (errore) {
      if (segnale?.aborted) throw errore; // Stop premuto: non è un problema di rete
      throw new ErroreLM(
        `Impossibile contattare LM Studio su ${this.baseUrl}: ` +
          "controlla che il server sia avviato e che la porta sia corretta."
      );
    }
    if (!risposta.ok) {
      await risposta.body?.cancel(); // anche la risposta di errore va chiusa
      throw new ErroreLM(`LM Studio ha risposto con un errore ${risposta.status}: ${risposta.statusText}`);
    }
    return risposta;
  }

  async _richiestaJson(metodo, endpoint, dati) {
    const risposta = await this._apri(metodo, endpoint, dati);
    try {
      return await risposta.json();
    } catch {
      throw new ErroreLM("Risposta non valida da LM Studio.");
    }
  }

  // Nomi dei modelli caricati in LM Studio
  async modelli() {
    const dati = await this._richiestaJson("GET", "models");
    return (dati.data ?? []).map((modello) => modello.id);
  }

  // Invia i messaggi e restituisce la risposta completa (stream disattivato)
  async chiedi(modello, messaggi) {
    const dati = await this._richiestaJson("POST", "chat/completions", {
      model: modello,
      messages: messaggi,
      stream: false,
    });
    const testo = dati?.choices?.[0]?.message?.content;
    if (typeof testo !== "string") throw new ErroreLM("Risposta non valida da LM Studio.");
    return testo.trim();
  }

  // Invia i messaggi con stream attivo e restituisce i pezzi di testo
  // uno alla volta, appena arrivano (si usa con "for await").
  //
  // Con lo streaming il server risponde in formato SSE: tante righe
  // "data: {...}" ognuna con un pezzetto di testo, e alla fine "data: [DONE]".
  // Per fermare la risposta a metà (pulsante Stop) si usa `segnale`:
  // la connessione si chiude e il generatore finisce senza errori.
  async *chiediStream(modello, messaggi, segnale) {
    try {
      const corpo = { model: modello, messages: messaggi, stream: true };
      const risposta = await this._apri("POST", "chat/completions", corpo, segnale);
      const decodificatore = new TextDecoder();
      let avanzo = ""; // l'ultima riga può arrivare a metà: si completa col pezzo dopo

      for await (const blocco of risposta.body) {
        const righe = (avanzo + decodificatore.decode(blocco, { stream: true })).split("\n");
        avanzo = righe.pop();
        for (let riga of righe) {
          riga = riga.trim();
          if (!riga.startsWith("data:")) continue;
          const dati = riga.slice("data:".length).trim();
          if (dati === "[DONE]") return;
          let scelte;
          try {
            scelte = JSON.parse(dati).choices ?? [];
          } catch {
            throw new ErroreLM("Risposta non valida da LM Studio.");
          }
          const pezzo = scelte[0]?.delta?.content;
          if (pezzo) yield pezzo;
        }
      }
    } catch (errore) {
      if (segnale?.aborted) return; // Stop premuto: si finisce in silenzio
      throw errore;
    }
  }
}

module.exports = { ClientLM, ErroreLM, configurazione, elencoModelli, leggiEnv, soloModelliChat };
