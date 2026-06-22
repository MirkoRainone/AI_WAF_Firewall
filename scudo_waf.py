import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse
from urllib.parse import unquote_plus, parse_qsl

class WafMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key # Salviamo la chiave del cliente

    async def dispatch(self, request, call_next):
        testo_da_analizzare = ""

        # ==========================================
        # 1. IL PORTAPACCHI (Cattura dati URL - GET)
        # ==========================================
        # Se l'URL è /?ricerca=<script>&id=5, request.query_params cattura tutto.
        if request.query_params:
            # Estraiamo SOLO i valori (es. "<script>", "5") e togliamo l'encoding
            valori_get = [unquote_plus(valore) for chiave, valore in request.query_params.items()]
            testo_da_analizzare += " ".join(valori_get) + " "

        # ==========================================
        # 2. IL BAGAGLIAIO (Cattura dati Body - POST/PUT/PATCH)
        # ==========================================
        if request.method in ["POST", "PUT", "PATCH"]:
            body_bytes = await request.body()
            testo_grezzo = body_bytes.decode('utf-8')

            # Pulizia dei dati del form web per l'IA
            dati_form = parse_qsl(testo_grezzo)
            if dati_form:
                # Se è un form, prendiamo solo i valori (scartiamo es. "indirizzo=")
                valori_post = [valore for chiave, valore in dati_form]
                testo_da_analizzare += " ".join(valori_post)
            else:
                # Se è testo puro, decodifichiamo e basta
                testo_da_analizzare += unquote_plus(testo_grezzo)

            # Trucco per permettere al sito del cliente di leggere i dati dopo di noi
            async def receive(): return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = receive

        # ==========================================
        # 3. LO SCANNER ASINCRONO
        # ==========================================
        testo_pulito = testo_da_analizzare.strip()

        if testo_pulito:
            try:
                url_render = "https://ai-waf-firewall.onrender.com/scansiona"
                
                # Chiamata fulminea che non blocca il server del cliente
                async with httpx.AsyncClient() as client:
                    risposta = await client.post(
                        url_render,
                        json={"testo": testo_pulito},
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=3.0 # Aspetta massimo 3 secondi
                    )
                
                # LOG SEGRETO PER IL TERMINALE
                print(f"🕵️ TESTO UNIVERSALE ANALIZZATO: {testo_pulito}")
                print(f"🤖 Risposta Render: {risposta.json()}")
                
                # SE IL WAF DICE CHE È UN HACKER, L'SDK BLOCCA TUTTO
                if risposta.status_code == 200 and risposta.json().get("status") == "403 Forbidden":
                    schermata_rossa = """
                    <html><body style='background:red; color:white; text-align:center; padding:50px; font-family:sans-serif;'>
                    <h1>🚨 MINACCIA BLOCCATA DAL WAF AI 🚨</h1>
                    <p>La tua richiesta è stata classificata come attacco informatico.</p>
                    <a href='/' style='color:yellow;'>Torna indietro</a>
                    </body></html>
                    """
                    return HTMLResponse(content=schermata_rossa, status_code=403)
            
            except Exception as e:
                # Se il WAF è offline, il sito del cliente CONTINUA A FUNZIONARE
                print(f"⚠️ Attenzione: Impossibile contattare il WAF ({e})")
                
        # 4. VIA LIBERA: Lascia passare la richiesta al sito del cliente
        return await call_next(request)