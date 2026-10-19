# Progetto_Scuola – Client per LM Studio

Raccolta di piccoli client Python, una lezione alla volta, per chattare con un
modello linguistico locale servito da [LM Studio](https://lmstudio.ai/).
Un menu nel terminale permette di scegliere quale versione avviare.

## Requisiti

- **Python 3.10 o successivo**
- **LM Studio** con il server locale avviato (scheda *Developer* → *Start Server*)
  e almeno un modello caricato
- Nessuna libreria esterna: si usa solo la libreria standard di Python
  (vedi `requirements.txt`)

## Installazione

```bash
# 1. (facoltativo) crea e attiva l'ambiente virtuale
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS

# 2. installa le dipendenze (al momento nessuna)
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
└── files_lezione_1/
    ├── client1.py       # senza streaming
    ├── client2.py       # con streaming
    └── client3.py       # streaming + memoria della chat
```

## Problemi comuni

- **"Impossibile contattare LM Studio"**: il server non è avviato, oppure la
  porta in `LM_BASE_URL` non è quella indicata da LM Studio.
- **Il modello cambiato non viene usato**: hai modificato `.env.example`
  invece di `.env`.
- **"timed out" o attesa molto lunga**: alcuni modelli (es. Qwen) "ragionano"
  a lungo prima di rispondere, e su un PC lento possono superare il limite di
  5 minuti. Prova un modello più piccolo, disattiva il ragionamento nelle
  impostazioni del modello in LM Studio, oppure controlla che il modello usi
  la scheda video (*GPU offload*).
