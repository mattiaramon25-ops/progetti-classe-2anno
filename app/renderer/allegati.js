// Allegati della chat: file e immagini da mandare al modello e codice da scaricare.
//
// Solo logica, niente grafica: lo usa app.js nella pagina e lo verificano
// i test con Node.js (per questo in fondo c'è module.exports).

const Allegati = (() => {
  const MB = 1024 * 1024;
  const LIMITE_IMMAGINE = 10 * MB;
  // Un testo lungo riempie la "memoria a breve termine" del modello (il contesto)
  const LIMITE_TESTO = 200 * 1024;

  // Formati di immagine che i modelli "vision" di LM Studio sanno leggere
  const TIPI_IMMAGINE = ["image/png", "image/jpeg", "image/webp", "image/gif"];

  // Estensioni per salvare il codice scritto dal modello
  const ESTENSIONI = {
    python: "py", py: "py",
    javascript: "js", js: "js", typescript: "ts", ts: "ts",
    html: "html", css: "css", json: "json", xml: "xml",
    bash: "sh", sh: "sh", shell: "sh", powershell: "ps1", ps1: "ps1", bat: "bat",
    java: "java", c: "c", cpp: "cpp", "c++": "cpp", csharp: "cs", cs: "cs",
    sql: "sql", markdown: "md", md: "md", yaml: "yml", yml: "yml", csv: "csv",
  };

  // Errore con un messaggio già comprensibile, da mostrare nella finestra
  class ErroreAllegato extends Error {
    constructor(messaggio) {
      super(messaggio);
      this.name = "ErroreAllegato";
    }
  }

  const dimensioneLeggibile = (byte) =>
    byte >= MB ? `${(byte / MB).toFixed(1)} MB` : `${Math.ceil(byte / 1024)} KB`;

  // btoa vuole una stringa con un carattere per byte: si costruisce a pezzi,
  // perché String.fromCharCode con milioni di argomenti andrebbe in errore
  function base64(bytes) {
    let binario = "";
    for (let i = 0; i < bytes.length; i += 0x8000) {
      binario += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    }
    return btoa(binario);
  }

  function bytesDaDataUrl(dataUrl) {
    const binario = atob(dataUrl.slice(dataUrl.indexOf(",") + 1));
    return Uint8Array.from(binario, (carattere) => carattere.charCodeAt(0));
  }

  // Un file è "di testo" se è UTF-8 valido e non contiene byte nulli
  // (i file binari come PDF, Word o ZIP ne hanno quasi sempre)
  function comeTesto(bytes) {
    try {
      const testo = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      return testo.includes("\u0000") ? null : testo;
    } catch {
      return null;
    }
  }

  // Trasforma un file scelto dall'utente in un allegato:
  //   { tipo: "immagine", nome, dataUrl }  oppure  { tipo: "testo", nome, testo }
  // Se il file non si può usare lancia un ErroreAllegato.
  function leggiAllegato(nome, mime, bytes) {
    if (mime.startsWith("image/") && !mime.startsWith("image/svg")) {
      if (!TIPI_IMMAGINE.includes(mime)) {
        throw new ErroreAllegato(`"${nome}": formato di immagine non supportato (usa PNG, JPEG, WebP o GIF).`);
      }
      if (bytes.length > LIMITE_IMMAGINE) {
        throw new ErroreAllegato(
          `"${nome}" è troppo grande (${dimensioneLeggibile(bytes.length)}): ` +
            `il massimo per un'immagine è ${dimensioneLeggibile(LIMITE_IMMAGINE)}.`
        );
      }
      return { tipo: "immagine", nome, dataUrl: `data:${mime};base64,${base64(bytes)}` };
    }
    if (bytes.length > LIMITE_TESTO) {
      throw new ErroreAllegato(
        `"${nome}" è troppo grande (${dimensioneLeggibile(bytes.length)}): ` +
          `il massimo per un file di testo è ${dimensioneLeggibile(LIMITE_TESTO)}.`
      );
    }
    const testo = comeTesto(bytes);
    if (testo === null) {
      throw new ErroreAllegato(
        `"${nome}": formato non supportato. Puoi allegare immagini e file di testo ` +
          "(.txt, .py, .js, .csv, .json, ...), non PDF o documenti Word."
      );
    }
    return { tipo: "testo", nome, testo };
  }

  // Prepara il "content" del messaggio da mandare a LM Studio.
  // - I file di testo vengono incollati in fondo alla domanda, con il loro nome.
  // - Senza immagini il contenuto resta una stringa, come nella lezione 1.
  // - Con le immagini diventa una lista di parti, nel formato delle API OpenAI:
  //   funziona solo con i modelli che sanno "vedere" (vision).
  function componiContenuto(testo, allegati) {
    let completo = testo;
    for (const file of allegati.filter((allegato) => allegato.tipo === "testo")) {
      const fine = file.testo.endsWith("\n") ? "" : "\n";
      completo += `${completo ? "\n\n" : ""}File "${file.nome}":\n\`\`\`\n${file.testo}${fine}\`\`\``;
    }
    const immagini = allegati.filter((allegato) => allegato.tipo === "immagine");
    if (immagini.length === 0) return completo;
    const parti = completo ? [{ type: "text", text: completo }] : [];
    for (const immagine of immagini) {
      parti.push({ type: "image_url", image_url: { url: immagine.dataUrl } });
    }
    return parti;
  }

  // Il testo di un contenuto, sia stringa sia lista di parti
  function testoDelContenuto(contenuto) {
    if (typeof contenuto === "string") return contenuto;
    return contenuto
      .filter((parte) => parte.type === "text")
      .map((parte) => parte.text)
      .join("\n");
  }

  // Blocchi di codice di una risposta: ```linguaggio ... ```
  function blocchiDiCodice(testo) {
    const blocchi = [];
    for (const trovato of testo.matchAll(/```([^\n`]*)\n([\s\S]*?)```/g)) {
      blocchi.push({ linguaggio: trovato[1].trim(), codice: trovato[2] });
    }
    return blocchi;
  }

  function nomeFileCodice(linguaggio, numero) {
    const chiave = linguaggio.toLowerCase();
    return `codice-${numero}.${Object.hasOwn(ESTENSIONI, chiave) ? ESTENSIONI[chiave] : "txt"}`;
  }

  return {
    LIMITE_IMMAGINE,
    LIMITE_TESTO,
    ErroreAllegato,
    leggiAllegato,
    componiContenuto,
    testoDelContenuto,
    blocchiDiCodice,
    nomeFileCodice,
    bytesDaDataUrl,
  };
})();

if (typeof module !== "undefined") module.exports = Allegati;
