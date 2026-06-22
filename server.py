from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import joblib
import os
import uvicorn

# Il server carica in memoria l'IA
model = joblib.load('cervello_waf.pkl')
vectorizer = joblib.load('traduttore_waf.pkl')

app = FastAPI()

class RichiestaWeb(BaseModel):
    testo: str

# ==========================================
# 💰 IL TUO DATABASE CLIENTI (Monetizzazione)
# ==========================================
# Qui inserisci le chiavi API di chi ha pagato l'abbonamento
CHIAVI_CLIENTI = [
    "Bearer sk_live_123456789",  # Cliente 1 (Tu)
    "Bearer sk_live_999888777"   # Cliente 2 (Esempio)
]

@app.post("/scansiona")
def analizza_traffico(richiesta: RichiestaWeb, authorization: str = Header(None)):
    
    # 1. IL CONTROLLO DEL BIGLIETTO ALL'INGRESSO
    if authorization not in CHIAVI_CLIENTI:
        # Se non c'è la chiave, o se la chiave è finta, blocca tutto con un errore 401
        raise HTTPException(status_code=401, detail="Accesso Negato: API Key non valida, mancante o abbonamento scaduto")

    # 2. SE IL CLIENTE PAGA, L'IA LAVORA
    testo_vettorizzato = vectorizer.transform([richiesta.testo])
    previsione = model.predict(testo_vettorizzato)

    if previsione[0] == 1:
        return {"status": "403 Forbidden", "messaggio": "🚨 ATTACCO BLOCCATO"}
    else:
        return {"status": "200 OK", "messaggio": "✅ Accesso consentito"}

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=porta)