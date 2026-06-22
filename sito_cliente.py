from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

# 1. IL CLIENTE IMPORTA IL TUO SDK
from scudo_waf import WafMiddleware

app = FastAPI()

# 2 e 3. IL CLIENTE ATTIVA LO SCUDO CON LA SUA API KEY
app.add_middleware(WafMiddleware, api_key="fake_api_key_del_cliente") # Sostituisci con la chiave reale del cliente

# ==========================================
# LE PAGINE DEL SITO (HTML)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def homepage():
    return """
    <html>
    <body style="font-family: Arial; text-align: center; margin-top: 100px; background-color: #f0f8ff;">
        <h1>🛒 Il mio E-commerce</h1>
        <p>Inserisci i tuoi dati di spedizione per completare l'ordine:</p>
        
        <form action="/paga" method="post">
            <input type="text" name="indirizzo" placeholder="Il tuo indirizzo..." 
                   style="padding: 10px; width: 300px; font-size: 16px;">
            <button type="submit" style="padding: 10px; background: blue; color: white;">Conferma Ordine</button>
        </form>
    </body>
    </html>
    """

@app.post("/paga", response_class=HTMLResponse)
async def pagamento_confermato(request: Request):
    # Se il codice arriva fin qui, significa che il WAF ha dato il permesso!
    form_data = await request.form()
    indirizzo = form_data.get("indirizzo", "")
    
    return f"""
    <html>
    <body style="font-family: Arial; text-align: center; margin-top: 100px; background-color: #e6ffe6;">
        <h1 style="color: green;">✅ Ordine Ricevuto!</h1>
        <p>Spediremo le scarpe all'indirizzo: <b>{indirizzo}</b></p>
        <a href="/">Torna al negozio</a>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)