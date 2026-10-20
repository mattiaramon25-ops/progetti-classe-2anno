"""Finto server LM Studio usato dai test (nessun LM Studio vero necessario)."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FintoLMStudio:
    """Piccolo server HTTP che imita le risposte di LM Studio.

    Le proprietà si possono cambiare in ogni test; le richieste ricevute
    vengono salvate in `richieste` per controllare cosa ha inviato il client.
    """

    def __init__(self):
        self.modelli = ["modello-a", "modello-b"]
        self.risposta = "  Ciao!  "
        self.pezzi = ["Ci", "ao", "!"]
        self.stato_http = 200
        self.ritardo = 0.0  # secondi di attesa prima di rispondere
        self.ritardo_pezzi = 0.0  # secondi tra un pezzo e l'altro dello streaming
        self.richieste: list[dict] = []

        finto = self

        class Gestore(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # niente log nel terminale durante i test

            def invia(self, corpo: bytes, tipo: str):
                time.sleep(finto.ritardo)
                self.send_response(finto.stato_http)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def invia_a_pezzi(self, corpo: bytes):
                """Manda le righe SSE una alla volta, come fa LM Studio."""
                time.sleep(finto.ritardo)
                self.send_response(finto.stato_http)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()  # niente Content-Length: la risposta finisce chiudendo
                try:
                    for evento in corpo.split(b"\n\n"):
                        self.wfile.write(evento + b"\n\n")
                        self.wfile.flush()
                        time.sleep(finto.ritardo_pezzi)
                except ConnectionError:
                    pass  # il client ha chiuso prima della fine (pulsante Stop)

            def do_GET(self):
                if self.path != "/v1/models":
                    self.send_error(404)
                    return
                dati = {"data": [{"id": nome} for nome in finto.modelli]}
                self.invia(json.dumps(dati).encode(), "application/json")

            def do_POST(self):
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                lunghezza = int(self.headers["Content-Length"])
                richiesta = json.loads(self.rfile.read(lunghezza))
                finto.richieste.append(richiesta)
                if richiesta.get("stream"):
                    self.invia_a_pezzi(finto.corpo_sse())
                else:
                    dati = {"choices": [{"message": {"content": finto.risposta}}]}
                    self.invia(json.dumps(dati).encode(), "application/json")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Gestore)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        ).start()

    def corpo_sse(self) -> bytes:
        """Righe "data: {...}" come le manda LM Studio, con qualche riga da ignorare."""
        righe = [": commento del server", "", 'data: {"choices": []}']
        righe.append('data: {"choices": [{"delta": {"role": "assistant"}}]}')
        for pezzo in self.pezzi:
            righe.append("data: " + json.dumps({"choices": [{"delta": {"content": pezzo}}]}))
        righe.append("data: [DONE]")
        righe.append("data: " + json.dumps({"choices": [{"delta": {"content": "DOPO"}}]}))
        return ("\n\n".join(righe) + "\n\n").encode()

    def chiudi(self):
        self.server.shutdown()
        self.server.server_close()
