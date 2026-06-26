import httpx
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse
from urllib.parse import unquote_plus, parse_qsl

class WafMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key 
        
        # 🧠 LA NUOVA MEMORIA LOCALE (Cache Anti-Spam)
        self.cache_attacchi = {}
        self.tempo_scadenza_cache = 60 # Ricorda l'attacco per 60 secondi

    async def dispatch(self, request, call_next):
        testo_da_analizzare = ""

        # 1. IL PORTAPACCHI (Cattura dati URL - GET)
        if request.query_params:
            valori_get = [unquote_plus(valore) for chiave, valore in request.query_params.items()]
            testo_da_analizzare += " ".join(valori_get) + " "

        # 2. IL BAGAGLIAIO (Cattura dati Body - POST/PUT/PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            body_bytes = await request.body()
            testo_grezzo = body_bytes.decode('utf-8')
            dati_form = parse_qsl(testo_grezzo)
            
            if dati_form:
                valori_post = [valore for chiave, valore in dati_form]
                testo_da_analizzare += " ".join(valori_post)
            else:
                testo_da_analizzare += unquote_plus(testo_grezzo)

            async def receive(): return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = receive

        # 3. LO SCANNER ASINCRONO
        testo_pulito = testo_da_analizzare.strip()
        
        # La schermata rossa pronta all'uso
        schermata_rossa = """
        <html><body style='background:red; color:white; text-align:center; padding:50px; font-family:sans-serif;'>
        <h1>🚨 MINACCIA BLOCCATA DAL WAF AI 🚨</h1>
        <p>La tua richiesta è stata classificata come attacco informatico.</p>
        <a href='/' style='color:yellow;'>Torna indietro</a>
        </body></html>
        """

        if testo_pulito:
            
            # 🧠 CONTROLLO NELLA CACHE (Prima di chiamare Render!)
            ora_attuale = time.time()
            if testo_pulito in self.cache_attacchi:
                tempo_registrazione = self.cache_attacchi[testo_pulito]
                if ora_attuale - tempo_registrazione < self.tempo_scadenza_cache:
                    print("🛡️ Bloccato dalla Cache locale! (Nessuna chiamata a Render)")
                    return HTMLResponse(content=schermata_rossa, status_code=403)
                else:
                    del self.cache_attacchi[testo_pulito] # Cache scaduta, puliamo

            try:
                url_render = "https://ai-waf-firewall.onrender.com/scansiona"
                
                async with httpx.AsyncClient() as client:
                    risposta = await client.post(
                        url_render,
                        json={"testo": testo_pulito},
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=3.0 
                    )
                
                if risposta.status_code == 200 and risposta.json().get("status") == "403 Forbidden":
                    # 🧠 SE È UN ATTACCO, SALVALO NELLA CACHE PER LA PROSSIMA VOLTA!
                    self.cache_attacchi[testo_pulito] = ora_attuale
                    return HTMLResponse(content=schermata_rossa, status_code=403)
            
            except Exception as e:
                print(f"⚠️ Attenzione: Impossibile contattare il WAF ({e})")
                
        # 4. VIA LIBERA
        return await call_next(request)