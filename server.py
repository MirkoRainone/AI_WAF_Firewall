import os
import uvicorn
import joblib
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from supabase import create_client, Client

# ==========================================
# 🗄️ COLLEGAMENTO DATABASE (Supabase)
# ==========================================
# (Nota: ho rimosso "/rest/v1/" dall'URL, la libreria vuole solo l'indirizzo base!)
SUPABASE_URL = "https://izghfwxmmeotrxpjbeym.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6Z2hmd3htbWVvdHJ4cGpiZXltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNTMzMzgsImV4cCI6MjA5NzcyOTMzOH0.LtxvympGKfgaJuEf0l6f9qMbLYyhMldM-2v6NDpxRYI"

# Inizializza il client del database
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 🧠 CARICAMENTO INTELLIGENZA ARTIFICIALE
# ==========================================
model = joblib.load('cervello_waf.pkl')
vectorizer = joblib.load('traduttore_waf.pkl')

app = FastAPI()

class RichiestaWeb(BaseModel):
    testo: str

@app.post("/scansiona")
def analizza_traffico(richiesta: RichiestaWeb, authorization: str = Header(None)):
    
    # 1. ESTRAZIONE DELLA CHIAVE
    if not authorization:
        raise HTTPException(status_code=401, detail="Accesso Negato: API Key mancante")
    
    # Puliamo la stringa togliendo "Bearer " per avere solo la chiave pura
    chiave_pulita = authorization.replace("Bearer ", "").strip()

    # 2. CONTROLLO SUL DATABASE SUPABASE (Il vero biglietto)
    # Cerchiamo nella tabella 'api_keys' se questa chiave esiste ed è attiva
    risposta_db = supabase.table("api_keys").select("*").eq("key_string", chiave_pulita).eq("is_active", True).execute()
    
    if len(risposta_db.data) == 0:
        # La lista 'data' è vuota: la chiave non esiste nel database!
        raise HTTPException(status_code=401, detail="Accesso Negato: API Key inesistente o disattivata")

    # 3. SE LA CHIAVE È VALIDA, L'IA LAVORA
    testo_vettorizzato = vectorizer.transform([richiesta.testo])
    previsione = model.predict(testo_vettorizzato)

    if previsione[0] == 1:
        # 🚨 ATTACCO RILEVATO!
        # Scriviamo il verbale nel database inserendo i dati nella tabella 'log_attacchi'
        supabase.table("log_attacchi").insert({
            "tipo_attacco": "Iniezione rilevata dall'IA",
            "payload_malevolo": richiesta.testo,
            "api_key_usata": chiave_pulita
        }).execute()

        return {"status": "403 Forbidden", "messaggio": "🚨 ATTACCO BLOCCATO"}
    else:
        # Nessun pericolo, lasciamo passare l'utente
        return {"status": "200 OK", "messaggio": "✅ Accesso consentito"}

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=porta)