from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import os

# Il server carica in memoria l'IA che hai appena "congelato"
model = joblib.load('modello_ai.pkl')
vectorizer = joblib.load('vectorizer.pkl')

# Creiamo l'app del server
app = FastAPI()

# Spieghiamo al server come sarà fatto il messaggio in arrivo
class RichiestaWeb(BaseModel):
    testo: str

# Creiamo la "porta" per ricevere gli attacchi
@app.post("/scansiona")
def analizza_traffico(richiesta: RichiestaWeb):
    
    # Traduciamo in numeri il testo appena ricevuto
    testo_vettorizzato = vectorizer.transform([richiesta.testo])
    
    # Facciamo fare la previsione all'IA
    previsione = model.predict(testo_vettorizzato)
    
    # Prepariamo la risposta da mandare indietro
    if previsione[0] == 1:
        return {"status": "403 Forbidden", "messaggio": "🚨 ATTACCO BLOCCATO"}
    else:
        return {"status": "200 OK", "messaggio": "✅ Accesso consentito"}
    

    if __name__ == "__main__":
        # Chiediamo al Cloud quale porta ci ha assegnato. Se siamo sul PC di casa, usa la 8000 di default.
        porta = int(os.environ.get("PORT", 8000))
        # Diciamo a Uvicorn di accendersi, ascoltando non più solo te (127.0.0.1) ma TUTTO il mondo (0.0.0.0)
        uvicorn.run(app, host="0.0.0.0", port=porta)