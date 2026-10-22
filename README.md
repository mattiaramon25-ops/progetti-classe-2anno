# Progetto_Scuola – Client per LM Studio

Raccolta di piccoli client Python, una lezione alla volta, per chattare con un
modello linguistico locale servito da [LM Studio](https://lmstudio.ai/).
Un menu nel terminale permette di scegliere quale versione avviare; in
alternativa c'è un'**interfaccia grafica** che riunisce le tre versioni in
un'unica finestra (vedi [Interfaccia grafica](#interfaccia-grafica)).

## Requisiti

- **Python 3.10 o successivo** per i client del terminale (usano solo la
  libreria standard: non serve installare niente)
- **Node.js 20 o successivo** per l'interfaccia grafica
  (scaricabile da [nodejs.org](https://nodejs.org/))
- **LM Studio** con il server locale avviato (scheda *Developer* → *Start Server*)
  e almeno un modello caricato

## Installazione

```bash
# 1. crea il file di configurazione partendo dall'esempio
copy .env.example .env           # Windows
# cp .env.example .env           # Linux / macOS

# 2. solo per l'interfaccia grafica: installa Electron
cd app
npm install
```

## Configurazione (`.env`)

I client leggono **solo** il file `.env`. Il file `.env.example` è soltanto un
modello da copiare: modificarlo non ha effetto.

| Variabile     | Significato                                   | Default                   |
|---------------|-----------------------------------------------|---------------------------|
| `LM_BASE_URL` | Indirizzo del server di LM Studio             | `http://localhost:1234`   |
| `LM_MODEL`    | Nome del modello da usare (come in LM Studio) | primo modello disponibile |

Esempio:

```
LM_BASE_URL=http://localhost:1234
LM_MODEL=spark-x2.5-4b@q8_0
```

Per vedere i nomi dei modelli disponibili:
<http://localhost:1234/v1/models>

## Avvio

```bash
python menu.py
```

Compare un menu con tutti gli applicativi, raggruppati per lezione:

```
=== Selettore applicativi ===

  Lezione 1
    1) client1.py
    2) client2.py
    3) client3.py

    0) Esci
```

Scrivi il numero e premi Invio. Dentro la chat scrivi `esci` per tornare al menu.
Puoi anche avviare un client direttamente, ad esempio
`python files_lezione_1/client1.py`.

## Interfaccia grafica

Una finestra per chattare con LM Studio senza usare il terminale, scritta in
**JavaScript con [Electron](https://www.electronjs.org/)**: la stessa
tecnologia di LM Studio. La grafica è una normale pagina HTML + CSS, per
questo scorrimento, streaming e animazioni sono fluidi.

```bash
cd app
npm start
```

Legge indirizzo e modello dallo stesso file `.env` dei client. Invece di tre
programmi separati, la finestra ha **una sola chat con due interruttori** nella
barra laterale, così si vede subito la differenza tra i client della lezione 1:

| Interruttore | Spento | Acceso |
|--------------|--------|--------|
| **Streaming** | risposta tutta insieme (come `client1`) | il testo compare pezzo per pezzo (come `client2`) |
| **Memoria**   | ogni domanda è indipendente | il modello ricorda la conversazione (come `client3`) |

### Cosa c'è nella finestra

- **Barra laterale** (si apre e si chiude con « / ☰ oppure **Ctrl+B**):
  - menu del **modello**, riempito in automatico con i modelli caricati in
    LM Studio (parte da `LM_MODEL` del `.env`, se impostato)
  - interruttori **Streaming** e **Memoria**
  - **Nuova chat**: svuota la conversazione e la memoria
  - **stato della connessione**: pallino verde = connesso, rosso lampeggiante
    = connessione in corso, rosso fisso = LM Studio non raggiungibile
  - **Tema scuro**: tema chiaro verde o scuro viola (all'inizio quello di Windows)
- **Chat**: all'avvio un saluto con tre domande d'esempio da cliccare; le
  risposte del modello mostrano il suo nome sopra la nuvoletta. Durante lo
  streaming la chat segue il testo, ma se scorri più su per rileggere resta
  ferma dove sei
- **Errori** (es. LM Studio spento) compaiono come avviso rosso nella chat,
  con il pulsante **Riprova**. Una domanda fallita o interrotta non entra
  nella memoria.

### File e immagini

**Upload** - si possono allegare file al messaggio in tre modi: con la
graffetta accanto alla casella (o **Ctrl+O**), trascinandoli sulla finestra,
oppure incollandoli (es. uno screenshot) con **Ctrl+V**. Prima di inviare
compaiono sopra la casella e si possono togliere con ✕.

| Tipo | Cosa riceve il modello | Limite |
|------|------------------------|--------|
| **Immagini** PNG, JPEG, WebP, GIF | l'immagine (formato `image_url` delle API OpenAI) | 10 MB |
| **File di testo** `.txt`, `.py`, `.js`, `.csv`, `.json`, ... | il contenuto, incollato in fondo alla domanda con il nome del file | 200 KB |

Le immagini funzionano solo con i modelli **vision** (che sanno "vedere",
es. Gemma 3 o Qwen-VL): con gli altri LM Studio risponde con un errore.
PDF e documenti Word non sono supportati: non sono testo semplice.

**Download** - ogni file scaricabile apre la finestra "Salva con nome"
(partendo dalla cartella Download):

- cliccando un'immagine o un file in un messaggio inviato
- **↓ Scarica risposta** sotto ogni risposta del modello (file `.md`)
- **↓ codice-1.py** (e simili) per ogni blocco di codice ```` ``` ```` nella
  risposta, con l'estensione giusta per il linguaggio

### Tasti

| Tasto | Azione |
|-------|--------|
| **Invio** | invia il messaggio |
| **Shift+Invio** | va a capo |
| **Esc** oppure ■ | ferma la risposta in corso |
| **Ctrl+N** | nuova chat |
| **Ctrl+B** | apre/chiude la barra laterale |
| **Ctrl+O** | allega file o immagini |
| **Ctrl+V** | nella casella: incolla anche immagini e file copiati |

### Preferenze

Tema, barra aperta/chiusa e interruttori vengono ricordati appena li cambi,
nel file `impostazioni_gui.json` (escluso da git). Per tornare ai valori
iniziali basta cancellarlo.

### Come funziona (per chi legge il codice)

Un'app Electron è fatta di due parti che si parlano con dei messaggi (IPC):

```
 renderer/ (la pagina)          preload.js            main.js (processo principale)
 HTML + CSS + app.js   ── window.lm.chiedi() ──▶   src/lm-api.js ──▶ LM Studio
 mostra la chat        ◀── "pezzo", risposta ───   (fetch, streaming SSE)
```

- `app/src/lm-api.js` contiene la logica per parlare con LM Studio, separata
  dalla grafica: è la stessa logica dei client della lezione 1 (lettura del
  `.env`, risposta normale e in streaming), senza stampe né input.
- `app/main.js` apre la finestra e fa le richieste a LM Studio. Con lo
  streaming manda alla pagina ogni pezzo di testo appena arriva; il pulsante
  Stop chiude la connessione con un `AbortController`.
- `app/preload.js` è il "ponte": la pagina non può usare Node.js né fare
  richieste da sola, ma solo le poche funzioni di `window.lm`. Le risposte del
  modello vengono sempre inserite come testo semplice (`textContent`), mai
  come HTML.
- `app/renderer/` è la grafica: `index.html` (struttura), `stile.css` (colori
  dei due temi, animazioni) e `app.js` (cosa succede quando si clicca).
  `allegati.js` contiene la logica degli allegati senza grafica (lettura dei
  file, messaggio con le immagini, blocchi di codice), verificata dai test.
- `app/src/file.js` salva i file scaricati: la pagina non può scrivere sul
  disco, quindi chiede a `main.js` (`window.lm.salvaFile()`), che mostra la
  finestra "Salva con nome".
  JavaScript non blocca mai la finestra mentre aspetta: usa `async`/`await`.

### Test

```bash
cd app
npm test
```

I test usano un **finto LM Studio** (`app/test/finto-lm.js`), quindi non serve
avere LM Studio acceso. Usano il test runner già incluso in Node.js.

## Lezioni

### Lezione 1 – `files_lezione_1/`

| File         | Streaming | Memoria della chat | Cosa mostra |
|--------------|:---------:|:------------------:|-------------|
| `client1.py` | no        | no                 | "il modello … sta pensando..." e poi la risposta tutta insieme |
| `client2.py` | sì        | no                 | la risposta compare pezzo per pezzo mentre il modello la genera |
| `client3.py` | sì        | sì                 | come client2, ma il modello ricorda la conversazione finché il client resta aperto |

- **Senza streaming** (`"stream": false`): il server restituisce la risposta
  completa in un'unica volta.
- **Con streaming** (`"stream": true`): il server invia tante righe
  `data: {...}` (formato SSE), ognuna con un pezzetto di testo, e chiude con
  `data: [DONE]`.
- **Memoria**: il modello non ricorda nulla da solo. `client3` conserva la
  lista di tutti i messaggi (domande e risposte) e la invia per intero a ogni
  nuova domanda. Chiudendo il client la memoria si azzera.

## Aggiungere una nuova lezione

Crea una cartella `files_lezione_<numero>` (es. `files_lezione_2`) e mettici
dentro i file `.py`: il menu li trova da solo, senza modificare `menu.py`.
I file il cui nome inizia con `_` vengono ignorati.

## Struttura

```
progetto_scuola/
├── menu.py              # menu di selezione degli applicativi
├── .env.example         # modello di configurazione
├── .env                 # configurazione reale (da creare)
├── requirements.txt
├── files_lezione_1/
│   ├── client1.py       # senza streaming
│   ├── client2.py       # con streaming
│   └── client3.py       # streaming + memoria della chat
└── app/                 # interfaccia grafica (Electron)
    ├── package.json     # nome, comandi (npm start, npm test) e dipendenze
    ├── main.js          # processo principale: finestra e richieste a LM Studio
    ├── preload.js       # ponte sicuro tra la pagina e main.js
    ├── src/
    │   ├── lm-api.js    # logica LM Studio (.env, modelli, chat, streaming)
    │   └── impostazioni.js  # preferenze salvate
    ├── renderer/        # la pagina mostrata nella finestra
    │   ├── index.html
    │   ├── stile.css    # colori dei temi, misure, animazioni
    │   └── app.js       # chat, barra laterale, tasti
    └── test/            # test (npm test) e finto LM Studio
```

## Problemi comuni

- **`'electron' non è riconosciuto...`** oppure **`Cannot find module`**: le
  dipendenze dell'interfaccia grafica non sono installate. Esegui
  `npm install` dentro la cartella `app`.
- **"Impossibile contattare LM Studio"**: il server non è avviato, oppure la
  porta in `LM_BASE_URL` non è quella indicata da LM Studio.
- **Il modello cambiato non viene usato**: hai modificato `.env.example`
  invece di `.env`.
- **"timed out" o attesa molto lunga**: alcuni modelli (es. Qwen) "ragionano"
  a lungo prima di rispondere, e su un PC lento i client del terminale possono
  superare il loro limite di 5 minuti (nell'interfaccia grafica si può sempre
  premere Stop). Prova un modello più piccolo, disattiva il ragionamento nelle
  impostazioni del modello in LM Studio, oppure controlla che il modello usi
  la scheda video (*GPU offload*).
