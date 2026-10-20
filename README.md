# Progetto_Scuola – Client per LM Studio

Raccolta di piccoli client Python, una lezione alla volta, per chattare con un
modello linguistico locale servito da [LM Studio](https://lmstudio.ai/).
Un menu nel terminale permette di scegliere quale versione avviare; in
alternativa c'è un'**interfaccia grafica** che riunisce le tre versioni in
un'unica finestra (vedi [Interfaccia grafica](#interfaccia-grafica)).

## Requisiti

- **Python 3.10 o successivo**
- **LM Studio** con il server locale avviato (scheda *Developer* → *Start Server*)
  e almeno un modello caricato
- I client del terminale usano solo la libreria standard di Python;
  l'interfaccia grafica usa **CustomTkinter** (vedi `requirements.txt`)

## Installazione

```bash
# 1. (facoltativo) crea e attiva l'ambiente virtuale
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS

# 2. installa le dipendenze (CustomTkinter, per l'interfaccia grafica)
pip install -r requirements.txt

# 3. crea il file di configurazione partendo dall'esempio
copy .env.example .env           # Windows
# cp .env.example .env           # Linux / macOS
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

Una finestra per chattare con LM Studio senza usare il terminale:

```bash
python app_grafica.py
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
  risposte del modello mostrano il suo nome sopra la nuvoletta
- **Errori** (es. LM Studio spento) compaiono come avviso rosso nella chat,
  con il pulsante **Riprova**. Una domanda fallita non entra nella memoria.

### Tasti

| Tasto | Azione |
|-------|--------|
| **Invio** | invia il messaggio |
| **Shift+Invio** | va a capo |
| **Esc** oppure ■ | ferma la risposta in corso |
| **Ctrl+N** | nuova chat |
| **Ctrl+B** | apre/chiude la barra laterale |

### Preferenze

Tema, barra aperta/chiusa e interruttori vengono ricordati alla chiusura nel
file `impostazioni_gui.json` (escluso da git). Per tornare ai valori iniziali
basta cancellarlo.

### Come funziona (per chi legge il codice)

- `gui/lm_api.py` contiene la logica per parlare con LM Studio, separata dalla
  grafica: è lo stesso codice dei client della lezione 1, senza `print()` né
  `input()`.
- Le richieste girano in un **thread separato** (`gui/esecutore.py`), così la
  finestra non si blocca mai. Tkinter però va usato solo dal thread della
  grafica: i risultati (anche i pezzi dello streaming) passano attraverso una
  coda che la finestra controlla con `after()`.

### Test

```bash
python -m unittest
```

I test usano un **finto LM Studio** (`tests/finto_lm.py`), quindi non serve
avere LM Studio acceso.

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
├── app_grafica.py       # avvio dell'interfaccia grafica
├── .env.example         # modello di configurazione
├── .env                 # configurazione reale (da creare)
├── requirements.txt
├── files_lezione_1/
│   ├── client1.py       # senza streaming
│   ├── client2.py       # con streaming
│   └── client3.py       # streaming + memoria della chat
├── gui/                 # interfaccia grafica
│   ├── lm_api.py        # logica LM Studio (.env, modelli, chat, streaming)
│   ├── esecutore.py     # lavoro in un thread, risultati alla grafica
│   ├── finestra.py      # finestra principale
│   ├── componenti.py    # nuvolette, barra laterale, barra di scrittura...
│   ├── animazione.py    # animazioni di barra laterale e menu
│   ├── impostazioni.py  # preferenze salvate
│   └── tema.py          # colori, font, misure
└── tests/               # test (python -m unittest)
```

## Problemi comuni

- **`ModuleNotFoundError: No module named 'customtkinter'`**: le dipendenze
  non sono installate nell'ambiente in uso. Attiva il `venv` ed esegui
  `pip install -r requirements.txt`.

- **"Impossibile contattare LM Studio"**: il server non è avviato, oppure la
  porta in `LM_BASE_URL` non è quella indicata da LM Studio.
- **Il modello cambiato non viene usato**: hai modificato `.env.example`
  invece di `.env`.
- **"timed out" o attesa molto lunga**: alcuni modelli (es. Qwen) "ragionano"
  a lungo prima di rispondere, e su un PC lento possono superare il limite di
  5 minuti. Prova un modello più piccolo, disattiva il ragionamento nelle
  impostazioni del modello in LM Studio, oppure controlla che il modello usi
  la scheda video (*GPU offload*).
