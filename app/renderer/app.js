// Logica della finestra: barra laterale, chat e barra di scrittura.
//
// La pagina non parla direttamente con LM Studio: usa window.lm
// (vedi preload.js) e le richieste vere partono da main.js.

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

// Invia il testo scritto nella casella (se c'è e se si può)
function invia() {
  if (richiesta) return; // il testo resta nella casella, pronto per dopo
  const testo = casella.value.trim();
  if (!testo) return;
  if (!connesso) {
    mostraErrore("Non sei connesso a LM Studio.", connetti);
    return;
  }
  casella.value = "";
  aggiungiMessaggio("utente", testo);
  chiedi(testo);
}

async function chiedi(testo) {
  if (richiesta) return;
  const domanda = { role: "user", content: testo };
  // Con la Memoria il modello "ricorda" la chat, altrimenti ogni domanda è indipendente
  const messaggi = interruttoreMemoria.checked ? [...cronologia, domanda] : [domanda];
  const id = ++ultimoNumero;
  const modello = modelloScelto;
  iniziaAttesa(id, modello);

  // Streaming (come client2): i pezzi arrivano a quandoArrivaUnPezzo, qui sotto.
  // Senza streaming (come client1): la risposta arriva tutta insieme.
  const esito = await lm.chiedi(id, modello, messaggi, interruttoreStreaming.checked);
  if (richiesta?.id !== id) return; // nel frattempo è stato premuto Stop

  const nuvoletta = nuvolettaInScrittura;
  fineAttesa();
  if (esito.errore) {
    mostraErrore(esito.errore, () => chiedi(testo));
  } else if (!esito.risposta) {
    aggiungiMessaggio("modello", "(nessuna risposta)", modello);
  } else {
    if (nuvoletta) nuvoletta.textContent = esito.risposta; // senza spazi finali
    else aggiungiMessaggio("modello", esito.risposta, modello);
    ricorda(testo, esito.risposta);
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

// Aggiunge un messaggio in fondo alla chat e restituisce la sua nuvoletta
function aggiungiMessaggio(mittente, testo, nomeModello) {
  colonna.querySelector(".benvenuto")?.remove(); // al primo messaggio il benvenuto sparisce
  const messaggio = document.createElement("div");
  messaggio.className = `messaggio ${mittente}`;
  if (mittente === "modello") {
    const nome = document.createElement("div");
    nome.className = "nome";
    nome.textContent = nomeModello;
    messaggio.append(nome);
  }
  const nuvoletta = document.createElement("div");
  nuvoletta.className = "nuvoletta";
  nuvoletta.textContent = testo;
  messaggio.append(nuvoletta);
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
function mostraErrore(messaggio, alRiprova) {
  const avviso = document.createElement("div");
  avviso.className = "avviso";
  const testo = document.createElement("span");
  testo.textContent = messaggio;
  const riprova = document.createElement("button");
  riprova.textContent = "↻  Riprova";
  riprova.addEventListener("click", () => {
    avviso.remove();
    alRiprova();
  });
  avviso.append(testo, riprova);
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
// Ctrl+B apre/chiude la barra, Ctrl+N nuova chat, Esc ferma la risposta
document.addEventListener("keydown", (evento) => {
  const tasto = evento.key.toLowerCase();
  if (evento.ctrlKey && tasto === "b") alternaBarra();
  else if (evento.ctrlKey && tasto === "n") nuovaChat();
  else if (tasto === "escape") {
    if (menuModello.classList.contains("aperto")) apriMenu(false);
    else ferma();
  } else return;
  evento.preventDefault();
});

avvia();
