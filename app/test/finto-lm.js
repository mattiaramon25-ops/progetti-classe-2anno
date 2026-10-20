// Finto server LM Studio usato dai test (nessun LM Studio vero necessario).
//
// Le proprietà si possono cambiare in ogni test; le richieste ricevute
// vengono salvate in `richieste` per controllare cosa ha inviato il client.

const http = require("node:http");

const aspetta = (ms) => new Promise((fatto) => setTimeout(fatto, ms));

class FintoLMStudio {
  constructor() {
    this.modelli = ["modello-a", "modello-b"];
    this.risposta = "  Ciao!  ";
    this.pezzi = ["Ci", "ao", "!"];
    this.statoHttp = 200;
    this.corpoNonValido = false; // true = risponde con testo che non è JSON
    this.ritardoPezzi = 0; // millisecondi tra un pezzo e l'altro dello streaming
    this.richieste = [];
    this.server = http.createServer((req, res) => this._gestisci(req, res));
  }

  // Avvia il server su una porta libera e restituisce il suo indirizzo
  async avvia() {
    await new Promise((fatto) => this.server.listen(0, "127.0.0.1", fatto));
    this.url = `http://127.0.0.1:${this.server.address().port}`;
    return this.url;
  }

  chiudi() {
    this.server.closeAllConnections();
    return new Promise((fatto) => this.server.close(fatto));
  }

  async _gestisci(req, res) {
    if (req.method === "GET" && req.url === "/v1/models") {
      const dati = { data: this.modelli.map((id) => ({ id })) };
      return this._invia(res, JSON.stringify(dati));
    }
    if (req.method === "POST" && req.url === "/v1/chat/completions") {
      let corpo = "";
      for await (const pezzo of req) corpo += pezzo;
      const richiesta = JSON.parse(corpo);
      this.richieste.push(richiesta);
      if (richiesta.stream) return this._inviaAPezzi(res);
      const dati = { choices: [{ message: { content: this.risposta } }] };
      return this._invia(res, JSON.stringify(dati));
    }
    res.writeHead(404).end();
  }

  _invia(res, corpo) {
    if (this.corpoNonValido) corpo = "questo non è JSON";
    res.writeHead(this.statoHttp, { "Content-Type": "application/json" });
    res.end(corpo);
  }

  // Manda le righe SSE una alla volta, come fa LM Studio
  async _inviaAPezzi(res) {
    res.writeHead(this.statoHttp, { "Content-Type": "text/event-stream" });
    for (const evento of this.corpoSse()) {
      if (res.destroyed) return; // il client ha chiuso prima della fine (pulsante Stop)
      res.write(evento + "\n\n");
      await aspetta(this.ritardoPezzi);
    }
    res.end();
  }

  // Righe "data: {...}" come le manda LM Studio, con qualche riga da ignorare
  corpoSse() {
    const righe = [": commento del server", 'data: {"choices": []}'];
    righe.push('data: {"choices": [{"delta": {"role": "assistant"}}]}');
    for (const pezzo of this.pezzi) {
      righe.push("data: " + JSON.stringify({ choices: [{ delta: { content: pezzo } }] }));
    }
    righe.push("data: [DONE]");
    righe.push("data: " + JSON.stringify({ choices: [{ delta: { content: "DOPO" } }] }));
    return righe;
  }
}

module.exports = { FintoLMStudio };
