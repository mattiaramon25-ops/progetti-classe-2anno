// Logica della finestra: barra laterale, chat e barra di scrittura.
//
// La pagina non parla direttamente con LM Studio: usa window.lm
// (vedi preload.js) e le richieste vere partono da main.js.
// La logica degli allegati sta in allegati.js (oggetto Allegati).

const ESEMPI = [
  "Spiegami cos'è un modello linguistico in tre frasi",
  "Dammi tre idee per un progetto di scuola in Python",
  "Scrivi una breve poesia sull'autunno",
];

// --- Elementi della pagina ---

const elemento = (id) => document.getElementById(id);
const barra = elemento("barra");
const chat = elemento("chat");
const colonna = elemento("colonna");
const casella = elemento("casella");
const pulsanteInvia = elemento("invia");
const menuModello = elemento("menu-modello");
const menuPulsante = elemento("menu-pulsante");
const menuLista = elemento("menu-lista");
const interruttoreStreaming = elemento("streaming");
const interruttoreMemoria = elemento("memoria");
const interruttoreTema = elemento("tema-scuro");
const sceltaFile = elemento("scegli-file");
const inAttesa = elemento("in-attesa");

// --- Stato dell'app ---

let preferenze = null; // tema, barra aperta, streaming, memoria (vedi src/impostazioni.js)
let connesso = false;
let modelloScelto = null;
// Memoria (come client3): gli scambi completi domanda/risposta della chat.
// Viene inviata al modello solo se l'interruttore Memoria è acceso.
let cronologia = [];
// Ogni domanda ha un numero: se l'utente preme Stop il numero attuale torna
// null, e le risposte che arrivano dopo per quello vecchio si ignorano.
let ultimoNumero = 0;
let richiesta = null; // { id, modello } della domanda in corso, oppure null
let nuvolettaInScrittura = null; // con lo streaming: la nuvoletta che sta crescendo
let indicatore = null; // "il modello sta pensando..."
// File e immagini scelti ma non ancora inviati (vedi allegati.js)
let allegatiInAttesa = [];

// --- Avvio ---

async function avvia() {
  ({ preferenze } = await lm.avvio());
  interruttoreStreaming.checked = preferenze.streaming;
  interruttoreMemoria.checked = preferenze.memoria;
  barra.classList.toggle("chiusa", !preferenze.barra_aperta);
  aggiornaTema();
  mostraBenvenuto();
  connetti();
}

// Chiede a LM Studio i modelli caricati
async function connetti() {
  impostaStato("connessione");
  const esito = await lm.modelli();
  if (esito.errore) {
    impostaStato("errore");
    mostraErrore(esito.errore, connetti);
    return;
  }
  riempiMenuModelli(esito.modelli, esito.scelto);
  impostaStato("connesso");
}

const STATI = {
  connessione: "Connessione...",
  connesso: "Connesso",
  errore: "Non connesso",
};

// Aggiorna il testo e il colore dei pallini (le classi sono usate in stile.css)
function impostaStato(stato) {
  connesso = stato === "connesso";
  elemento("testo-stato").textContent = STATI[stato];
  document.body.classList.toggle("connesso", connesso);
  document.body.classList.toggle("in-connessione", stato === "connessione");
}

// --- Domanda e risposta ---

// Invia il testo scritto nella casella e gli allegati (se ci sono e se si può)
function invia() {
  if (richiesta) return; // testo e allegati restano, pronti per dopo
  const testo = casella.value.trim();
  if (!testo && allegatiInAttesa.length === 0) return;
  if (!connesso) {
    mostraErrore("Non sei connesso a LM Studio.", connetti);
    return;
  }
  const allegati = allegatiInAttesa;
  casella.value = "";
  allegatiInAttesa = [];
  mostraAllegatiInAttesa();
  aggiungiMessaggio("utente", testo, null, allegati);
  chiedi(Allegati.componiContenuto(testo, allegati));
}

// `contenuto` è il testo della domanda, oppure una lista di parti
// se ci sono immagini (vedi componiContenuto in allegati.js)
async function chiedi(contenuto) {
  if (richiesta) return;
  const domanda = { role: "user", content: contenuto };
  // Con la Memoria il modello "ricorda" la chat, altrimenti ogni domanda è indipendente
  const messaggi = interruttoreMemoria.checked ? [...cronologia, domanda] : [domanda];
  const id = ++ultimoNumero;
  const modello = modelloScelto;
  iniziaAttesa(id, modello);

  // Streaming (come client2): i pezzi arrivano a quandoArrivaUnPezzo, qui sotto.
  // Senza streaming (come client1): la risposta arriva tutta insieme.
  const esito = await lm.chiedi(id, modello, messaggi, interruttoreStreaming.checked);
  if (richiesta?.id !== id) return; // nel frattempo è stato premuto Stop

  let nuvoletta = nuvolettaInScrittura;
  fineAttesa();
  if (esito.errore) {
    // Le immagini le capiscono solo i modelli "vision": è l'errore più probabile
    const conImmagini = messaggi.some((messaggio) => Array.isArray(messaggio.content));
    const consiglio = conImmagini ? " Se il modello non sa leggere le immagini, scegline uno vision." : "";
    const messaggio = conImmagini ? esito.errore.replace(/\.?$/, ".") + consiglio : esito.errore;
    mostraErrore(messaggio, () => chiedi(contenuto));
  } else if (!esito.risposta) {
    aggiungiMessaggio("modello", "(nessuna risposta)", modello);
  } else {
    if (nuvoletta) nuvoletta.textContent = esito.risposta; // senza spazi finali
    else nuvoletta = aggiungiMessaggio("modello", esito.risposta, modello);
    aggiungiPulsantiScarica(nuvoletta.parentElement, esito.risposta);
    ricorda(contenuto, esito.risposta);
  }
}

lm.quandoArrivaUnPezzo((id, pezzo) => {
  if (richiesta?.id !== id) return; // pezzo di una risposta già fermata
  if (!nuvolettaInScrittura) {
    pezzo = pezzo.trimStart(); // spazi e righe vuote iniziali non servono
    if (!pezzo) return;
    // al primo pezzo vero la nuvoletta prende il posto di "sta pensando..."
    togliIndicatore();
    nuvolettaInScrittura = aggiungiMessaggio("modello", "", richiesta.modello);
    nuvolettaInScrittura.classList.add("in-scrittura");
  }
  const restaInFondo = vicinoAlFondo(); // se l'utente sta rileggendo più su, non lo spostiamo
  nuvolettaInScrittura.append(pezzo);
  if (restaInFondo) scorriInFondo(false);
});

// Solo gli scambi completi entrano in memoria: le domande fallite o
// interrotte restano fuori, come in client3
// (domanda può contenere immagini: con la Memoria vengono rimandate ogni volta)
function ricorda(domanda, risposta) {
  cronologia.push({ role: "user", content: domanda });
  cronologia.push({ role: "assistant", content: risposta });
}

function iniziaAttesa(id, modello) {
  richiesta = { id, modello };
  pulsanteInvia.textContent = "■";
  pulsanteInvia.title = "Ferma la risposta (Esc)";
  indicatore = creaPensiero(modello);
  colonna.append(indicatore);
  scorriInFondo();
}

function fineAttesa() {
  richiesta = null;
  pulsanteInvia.textContent = "➤";
  pulsanteInvia.title = "Invia (Invio)";
  togliIndicatore();
  nuvolettaInScrittura?.classList.remove("in-scrittura");
  nuvolettaInScrittura = null;
}

function togliIndicatore() {
  indicatore?.remove();
  indicatore = null;
}

// Pulsante Stop o tasto Esc: smette di aspettare la risposta.
// Il testo già arrivato resta; quello che arriva dopo viene ignorato.
function ferma(mostraNota = true) {
  if (!richiesta) return;
  lm.ferma(richiesta.id); // lo streaming si chiude subito
  fineAttesa();
  if (!mostraNota) return;
  const nota = document.createElement("div");
  nota.className = "nota";
  nota.textContent = "Risposta interrotta";
  colonna.append(nota);
  scorriInFondo();
}

// Svuota la chat e la memoria. Il testo nella casella resta.
function nuovaChat() {
  ferma(false);
  colonna.replaceChildren();
  cronologia = [];
  mostraBenvenuto();
  casella.focus();
}

// --- Contenuto della chat ---
// I testi vengono sempre inseriti come testo semplice (mai come HTML),
// così una risposta del modello non può modificare la pagina.

// Aggiunge un messaggio in fondo alla chat e restituisce la sua nuvoletta.
// I messaggi dell'utente possono avere degli allegati: si scaricano cliccandoli.
function aggiungiMessaggio(mittente, testo, nomeModello, allegati = []) {
  colonna.querySelector(".benvenuto")?.remove(); // al primo messaggio il benvenuto sparisce
  const messaggio = document.createElement("div");
  messaggio.className = `messaggio ${mittente}`;
  if (mittente === "modello") {
    const nome = document.createElement("div");
    nome.className = "nome";
    nome.textContent = nomeModello;
    messaggio.append(nome);
  }
  if (allegati.length > 0) {
    const elenco = document.createElement("div");
    elenco.className = "allegati";
    for (const allegato of allegati) {
      const pulsante = creaAllegato(allegato, "button");
      pulsante.title = `Scarica ${allegato.nome}`;
      pulsante.addEventListener("click", () => scaricaAllegato(allegato));
      elenco.append(pulsante);
    }
    messaggio.append(elenco);
  }
  const nuvoletta = document.createElement("div");
  nuvoletta.className = "nuvoletta";
  nuvoletta.textContent = testo;
  // un messaggio con solo allegati non ha bisogno della nuvoletta
  if (testo || mittente === "modello") messaggio.append(nuvoletta);
  colonna.append(messaggio);
  scorriInFondo();
  return nuvoletta;
}

function creaPensiero(modello) {
  const messaggio = document.createElement("div");
  messaggio.className = "messaggio modello";
  const nuvoletta = document.createElement("div");
  nuvoletta.className = "nuvoletta pensiero";
  nuvoletta.textContent = `${modello} sta pensando`;
  const puntini = document.createElement("span");
  puntini.className = "puntini";
  for (let i = 0; i < 3; i++) {
    const puntino = document.createElement("span");
    puntino.textContent = ".";
    puntini.append(puntino);
  }
  nuvoletta.append(puntini);
  messaggio.append(nuvoletta);
  return messaggio;
}

// Avviso rosso in fondo alla chat, con il pulsante Riprova
// (oppure Chiudi, se non c'è niente da riprovare)
function mostraErrore(messaggio, alRiprova) {
  const avviso = document.createElement("div");
  avviso.className = "avviso";
  const testo = document.createElement("span");
  testo.textContent = messaggio;
  const pulsante = document.createElement("button");
  pulsante.textContent = alRiprova ? "↻  Riprova" : "Chiudi";
  pulsante.addEventListener("click", () => {
    avviso.remove();
    alRiprova?.();
  });
  avviso.append(testo, pulsante);
  colonna.append(avviso);
  scorriInFondo();
}

// Benvenuto mostrato quando la chat è vuota, con domande d'esempio cliccabili
function mostraBenvenuto() {
  const benvenuto = document.createElement("div");
  benvenuto.className = "benvenuto";
  const titolo = document.createElement("h2");
  titolo.textContent = "Ciao! Come posso aiutarti?";
  const sottotitolo = document.createElement("p");
  sottotitolo.textContent = "Scrivi una domanda qui sotto oppure prova uno di questi esempi:";
  benvenuto.append(titolo, sottotitolo);
  for (const esempio of ESEMPI) {
    const pulsante = document.createElement("button");
    pulsante.className = "esempio";
    pulsante.textContent = esempio;
    pulsante.addEventListener("click", () => {
      casella.value = esempio;
      invia(); // se non si può inviare, l'esempio resta nella casella
    });
    benvenuto.append(pulsante);
  }
  colonna.append(benvenuto);
}

function vicinoAlFondo() {
  return chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80;
}

// Scorre fino all'ultimo messaggio. Con lo streaming arrivano tanti pezzi:
// lo scorrimento avviene al massimo una volta per fotogramma.
let scorrimentoProgrammato = false;
function scorriInFondo(morbido = true) {
  if (scorrimentoProgrammato) return;
  scorrimentoProgrammato = true;
  requestAnimationFrame(() => {
    scorrimentoProgrammato = false;
    chat.scrollTo({ top: chat.scrollHeight, behavior: morbido ? "smooth" : "instant" });
  });
}

// --- Allegati: upload ---

// Legge i file scelti (con la graffetta, trascinati o incollati) e li mette
// in attesa sopra la casella. Quelli che non vanno bene mostrano un avviso.
async function aggiungiFile(file) {
  for (const singolo of file) {
    try {
      const bytes = new Uint8Array(await singolo.arrayBuffer());
      allegatiInAttesa.push(Allegati.leggiAllegato(singolo.name, singolo.type, bytes));
    } catch (errore) {
      const messaggio =
        errore instanceof Allegati.ErroreAllegato ? errore.message : `Impossibile leggere "${singolo.name}".`;
      mostraErrore(messaggio);
    }
  }
  mostraAllegatiInAttesa();
  casella.focus();
}

function mostraAllegatiInAttesa() {
  inAttesa.replaceChildren();
  for (const allegato of allegatiInAttesa) {
    const voce = creaAllegato(allegato, "div");
    const togli = document.createElement("button");
    togli.type = "button";
    togli.className = "togli";
    togli.textContent = "✕";
    togli.title = `Togli ${allegato.nome}`;
    togli.addEventListener("click", () => {
      allegatiInAttesa = allegatiInAttesa.filter((altro) => altro !== allegato);
      mostraAllegatiInAttesa();
    });
    voce.append(togli);
    inAttesa.append(voce);
  }
  inAttesa.hidden = allegatiInAttesa.length === 0;
}

// Un allegato: miniatura dell'immagine (o etichetta con l'estensione) e nome
function creaAllegato(allegato, tag) {
  const voce = document.createElement(tag);
  voce.className = `allegato ${allegato.tipo}`;
  if (tag === "button") voce.type = "button";
  if (allegato.tipo === "immagine") {
    const immagine = document.createElement("img");
    immagine.src = allegato.dataUrl;
    immagine.alt = allegato.nome;
    voce.append(immagine);
    // nei messaggi inviati si vede solo l'immagine, in grande
    if (tag === "button") return voce;
  } else {
    const icona = document.createElement("span");
    icona.className = "icona-file";
    const estensione = allegato.nome.includes(".") ? allegato.nome.split(".").pop() : "";
    icona.textContent = estensione.slice(0, 4) || "txt";
    voce.append(icona);
  }
  const nome = document.createElement("span");
  nome.className = "nome-file";
  nome.textContent = allegato.nome;
  voce.append(nome);
  return voce;
}

// --- Allegati: download ---

// main.js chiede dove salvare: se l'utente annulla non succede niente
async function scarica(nome, contenuto) {
  const esito = await lm.salvaFile(nome, contenuto);
  if (esito.errore) mostraErrore(esito.errore, () => scarica(nome, contenuto));
}

function scaricaAllegato(allegato) {
  if (allegato.tipo === "immagine") scarica(allegato.nome, Allegati.bytesDaDataUrl(allegato.dataUrl));
  else scarica(allegato.nome, allegato.testo);
}

// Sotto una risposta: "Scarica risposta" e un pulsante per ogni blocco di codice
function aggiungiPulsantiScarica(messaggio, risposta) {
  const azioni = document.createElement("div");
  azioni.className = "azioni";
  const aggiungiPulsante = (testo, titolo, alClick) => {
    const pulsante = document.createElement("button");
    pulsante.textContent = testo;
    pulsante.title = titolo;
    pulsante.addEventListener("click", alClick);
    azioni.append(pulsante);
  };
  aggiungiPulsante("↓ Scarica risposta", "Salva la risposta in un file", () => scarica("risposta.md", risposta));
  Allegati.blocchiDiCodice(risposta).forEach(({ linguaggio, codice }, indice) => {
    const nome = Allegati.nomeFileCodice(linguaggio, indice + 1);
    aggiungiPulsante(`↓ ${nome}`, "Salva questo codice in un file", () => scarica(nome, codice));
  });
  messaggio.append(azioni);
}

// --- Menu dei modelli ---

function riempiMenuModelli(modelli, scelto) {
  menuLista.replaceChildren();
  for (const nome of modelli) {
    const voce = document.createElement("li");
    voce.role = "option";
    voce.textContent = nome;
    voce.addEventListener("click", () => {
      scegliModello(nome);
      apriMenu(false);
    });
    menuLista.append(voce);
  }
  menuPulsante.disabled = false;
  scegliModello(scelto);
}

function scegliModello(nome) {
  modelloScelto = nome;
  elemento("modello-scelto").textContent = nome;
  for (const voce of menuLista.children) {
    voce.ariaSelected = String(voce.textContent === nome);
  }
}

function apriMenu(aperto) {
  menuModello.classList.toggle("aperto", aperto);
  menuPulsante.ariaExpanded = String(aperto);
}

menuPulsante.addEventListener("click", () => apriMenu(!menuModello.classList.contains("aperto")));
document.addEventListener("click", (evento) => {
  if (!menuModello.contains(evento.target)) apriMenu(false); // click fuori dal menu
});

// --- Barra laterale, tema e preferenze ---

function alternaBarra() {
  barra.classList.toggle("chiusa");
  apriMenu(false);
  salvaPreferenze();
}

// L'interruttore e l'icona del tema mostrano il tema attivo
// (quello di Windows, finché l'utente non ne sceglie uno)
function aggiornaTema() {
  const scuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
  interruttoreTema.checked = scuro;
  elemento("tema-icona").textContent = scuro ? "☀" : "☾"; // il tema in cui si passa cliccando
}

function cambiaTema(scuro) {
  preferenze.tema = scuro ? "dark" : "light";
  salvaPreferenze(); // main.js cambia il tema: la pagina se ne accorge da sola
}

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", aggiornaTema);

function salvaPreferenze() {
  preferenze.barra_aperta = !barra.classList.contains("chiusa");
  preferenze.streaming = interruttoreStreaming.checked;
  preferenze.memoria = interruttoreMemoria.checked;
  lm.salvaPreferenze(preferenze);
}

// --- Pulsanti e tasti ---

elemento("chiudi-barra").addEventListener("click", alternaBarra);
elemento("apri-barra").addEventListener("click", alternaBarra);
elemento("nuova-chat").addEventListener("click", nuovaChat);
elemento("nuova-chat-icona").addEventListener("click", nuovaChat);
interruttoreStreaming.addEventListener("change", salvaPreferenze);
interruttoreMemoria.addEventListener("change", salvaPreferenze);
interruttoreTema.addEventListener("change", () => cambiaTema(interruttoreTema.checked));
elemento("allega").addEventListener("click", () => sceltaFile.click());

sceltaFile.addEventListener("change", () => {
  aggiungiFile([...sceltaFile.files]);
  sceltaFile.value = ""; // così si può scegliere di nuovo lo stesso file
});

// Incollare un'immagine (es. uno screenshot) o un file copiato lo allega;
// il testo normale si incolla come sempre
casella.addEventListener("paste", (evento) => {
  const file = [...evento.clipboardData.files];
  if (file.length === 0) return;
  evento.preventDefault();
  aggiungiFile(file);
});

// Trascinare file sulla finestra. Senza preventDefault Electron aprirebbe
// il file al posto della chat. Il contatore serve perché dragenter/dragleave
// scattano anche passando sopra ogni elemento della pagina.
let trascinamenti = 0;
const trascinaFile = (evento) => evento.dataTransfer.types.includes("Files");
document.addEventListener("dragenter", (evento) => {
  if (!trascinaFile(evento)) return;
  trascinamenti++;
  document.body.classList.add("trascinamento");
});
document.addEventListener("dragleave", (evento) => {
  if (!trascinaFile(evento)) return;
  trascinamenti = Math.max(0, trascinamenti - 1);
  if (trascinamenti === 0) document.body.classList.remove("trascinamento");
});
document.addEventListener("dragover", (evento) => evento.preventDefault());
document.addEventListener("drop", (evento) => {
  evento.preventDefault();
  trascinamenti = 0;
  document.body.classList.remove("trascinamento");
  if (evento.dataTransfer.files.length > 0) aggiungiFile([...evento.dataTransfer.files]);
});
elemento("tema-icona").addEventListener("click", () => cambiaTema(!interruttoreTema.checked));

// Il pulsante a destra della casella è "Invia" oppure, mentre si aspetta, "Stop"
elemento("scrittura").addEventListener("submit", (evento) => {
  evento.preventDefault(); // un form normalmente ricarica la pagina
  if (richiesta) ferma();
  else invia();
});

casella.addEventListener("keydown", (evento) => {
  // Invio manda il messaggio, Shift+Invio va a capo
  if (evento.key === "Enter" && !evento.shiftKey && !evento.isComposing) {
    evento.preventDefault();
    invia();
  }
});

// Scorciatoie, attive anche mentre si scrive nella casella:
// Ctrl+B apre/chiude la barra, Ctrl+N nuova chat, Ctrl+O allega file,
// Esc ferma la risposta
document.addEventListener("keydown", (evento) => {
  const tasto = evento.key.toLowerCase();
  if (evento.ctrlKey && tasto === "b") alternaBarra();
  else if (evento.ctrlKey && tasto === "n") nuovaChat();
  else if (evento.ctrlKey && tasto === "o") sceltaFile.click();
  else if (tasto === "escape") {
    if (menuModello.classList.contains("aperto")) apriMenu(false);
    else ferma();
  } else return;
  evento.preventDefault();
});

avvia();
