import requests
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse

class WafMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key  # Salviamo la chiave del cliente

    async def dispatch(self, request, call_next):
        # Controlliamo solo i dati che gli utenti inviano al sito (POST)
        if request.method == "POST":
            body_bytes = await request.body()
            testo_grezzo = body_bytes.decode('utf-8')
            
            # Trucco per permettere al sito del cliente di leggere i dati dopo di noi
            async def receive(): return {"type": "http.request", "body": body_bytes,"more_body": False}
            request._receive = receive

            if testo_grezzo:
                try:
                    # IL TUO SDK CHIAMA IL TUO SERVER RENDER
                    url_render = "https://ai-waf-firewall.onrender.com/scansiona"
                    
                    # Inviamo il testo e facciamo vedere il pass VIP (API Key)
                    risposta = requests.post(
                        url_render, 
                        json={"testo": testo_grezzo},
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=3 # Aspetta massimo 3 secondi
                    )
                    # AGGIUNGI QUESTA RIGA PER SPIARE COSA DICE RENDER:
                    print(f"🕵️ LOG SEGRETO - Render ha risposto: {risposta.json()}")
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
                    # Se il tuo server Render è offline, facciamo passare l'utente 
                    # per non far crollare il sito del cliente.
                    print(f"Attenzione: Impossibile contattare il WAF ({e})")

        # Se è tutto pulito (o se l'utente sta solo guardando la pagina), lascia passare
        return await call_next(request)