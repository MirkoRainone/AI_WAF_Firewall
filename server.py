import os
import time
import uvicorn
import joblib
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from supabase import create_client, Client

# ==========================================
# 🗄️ COLLEGAMENTO DATABASE (Supabase)
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("🚨 ERRORE FATALE: Variabili d'ambiente SUPABASE mancanti!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 🧠 CARICAMENTO INTELLIGENZA ARTIFICIALE
# ==========================================
model = joblib.load('cervello_waf.pkl')
vectorizer = joblib.load('traduttore_waf.pkl')

app = FastAPI()

class RichiestaWeb(BaseModel):
    testo: str

# ==========================================
# 🚦 SISTEMA DI RATE LIMITING (Anti-DDoS)
# ==========================================
# Memoria che tiene traccia degli accessi: { "chiave_api": [orario1, orario2, ...] }
registro_traffico = {}
MAX_RICHIESTE_AL_MINUTO = 60

@app.post("/scansiona")
def analizza_traffico(richiesta: RichiestaWeb, authorization: str = Header(None)):
    
    # 1. ESTRAZIONE DELLA CHIAVE
    if not authorization:
        raise HTTPException(status_code=401, detail="Accesso Negato: API Key mancante")
    
    chiave_pulita = authorization.replace("Bearer ", "").strip()

    # 2. CONTROLLO RATE LIMITING (Prima ancora di disturbare il Database!)
    ora_attuale = time.time()
    
    # Se è la prima volta che vediamo questa chiave, creiamo la sua lista
    if chiave_pulita not in registro_traffico:
        registro_traffico[chiave_pulita] = []
        
    # Puliamo la lista: teniamo solo le richieste fatte negli ultimi 60 secondi
    registro_traffico[chiave_pulita] = [t for t in registro_traffico[chiave_pulita] if ora_attuale - t < 60]
    
    # Controlliamo se ha superato il limite
    if len(registro_traffico[chiave_pulita]) >= MAX_RICHIESTE_AL_MINUTO:
        raise HTTPException(status_code=429, detail="Too Many Requests: Hai superato il limite di 60 richieste al minuto.")
        
    # Se è tutto ok, registriamo questo nuovo accesso
    registro_traffico[chiave_pulita].append(ora_attuale)

    # 3. CONTROLLO SUL DATABASE SUPABASE
    risposta_db = supabase.table("api_keys").select("*").eq("key_string", chiave_pulita).eq("is_active", True).execute()
    
    if len(risposta_db.data) == 0:
        raise HTTPException(status_code=401, detail="Accesso Negato: API Key inesistente o disattivata")

    # 4. L'IA LAVORA
    testo_vettorizzato = vectorizer.transform([richiesta.testo])
    previsione = model.predict(testo_vettorizzato)

    if previsione[0] == 1:
        supabase.table("log_attacchi").insert({
            "tipo_attacco": "Iniezione rilevata dall'IA",
            "payload_malevolo": richiesta.testo,
            "api_key_usata": chiave_pulita
        }).execute()

        return {"status": "403 Forbidden", "messaggio": "🚨 ATTACCO BLOCCATO"}
    else:
        return {"status": "200 OK", "messaggio": "✅ Accesso consentito"}

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=porta)