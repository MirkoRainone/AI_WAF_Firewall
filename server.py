import os
import time
import uvicorn
import joblib
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks # <-- NUOVO: BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
from cachetools import TTLCache # <-- NUOVO: Cache ad alte prestazioni

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

app = FastAPI(title="WAF AI Production Server")

class RichiestaWeb(BaseModel):
    testo: str

# ==========================================
# 🧠 SISTEMA DI CACHING (Performance di Mercato)
# ==========================================
# Memorizza le API Key valide per 5 minuti (300 secondi). Massimo 5000 client contemporanei.
# Questo evita di tempestare Supabase di query identiche!
cache_chiavi_valide = TTLCache(maxsize=5000, ttl=300)

# Rate Limiter sicuro: si auto-pulisce ogni 60 secondi salvando la RAM del server
registro_traffico = TTLCache(maxsize=10000, ttl=60)
MAX_RICHIESTE_AL_MINUTO = 60

# ==========================================
# 🦥 FUNZIONI IN BACKGROUND (Asincrone)
# ==========================================
def esegui_logging_supabase(testo: str, chiave: str):
    """Scrive i log su Supabase in background senza far aspettare il cliente"""
    try:
        supabase.table("log_attacchi").insert({
            "tipo_attacco": "Iniezione rilevata dall'IA",
            "payload_malevolo": testo,
            "api_key_usata": chiave
        }).execute()
        print("💾 Log dell'attacco salvato su Supabase in background.")
    except Exception as e:
        print(f"❌ Errore durante il salvataggio del log asincrono: {e}")

# ==========================================
# 🚦 ENDPOINT PRINCIPALE
# ==========================================
@app.post("/scansiona")
async def analizza_traffico(richiesta: RichiestaWeb, background_tasks: BackgroundTasks, authorization: str = Header(None)):
    
    # 1. ESTRAZIONE DELLA CHIAVE
    if not authorization:
        raise HTTPException(status_code=401, detail="Accesso Negato: API Key mancante")
    
    chiave_pulita = authorization.replace("Bearer ", "").strip()

    # 2. CONTROLLO RATE LIMITING (Ottimizzato con TTLCache)
    ora_attuale = time.time()
    
    if chiave_pulita not in registro_traffico:
        registro_traffico[chiave_pulita] = []
        
    # Essendo una TTLCache, gli elementi vecchi di 60s decadono, ma facciamo una pulizia rapida dei timestamp interni
    registro_traffico[chiave_pulita] = [t for t in registro_traffico[chiave_pulita] if ora_attuale - t < 60]
    
    if len(registro_traffico[chiave_pulita]) >= MAX_RICHIESTE_AL_MINUTO:
        raise HTTPException(status_code=429, detail="Too Many Requests: Limite superato.")
        
    registro_traffico[chiave_pulita].append(ora_attuale)

    # 3. VERIFICA API KEY (Prima cerchiamo in Cache, poi su Supabase)
    if chiave_pulita in cache_chiavi_valide:
        # La chiave è in cache ed è valida, saltiamo la chiamata a Supabase!
        pass
    else:
        # Non è in cache, dobbiamo chiedere a Supabase
        try:
            risposta_db = supabase.table("api_keys").select("*").eq("key_string", chiave_pulita).eq("is_active", True).execute()
            if len(risposta_db.data) == 0:
                raise HTTPException(status_code=401, detail="Accesso Negato: API Key non valida")
            
            # Se è valida, salviamola nella memoria locale per i prossimi 5 minuti
            cache_chiavi_valide[chiave_pulita] = True
        except HTTPException:
            raise
        except Exception as e:
            # Fallback di sicurezza se Supabase ha problemi: lasciamo decidere se far passare (Fail-Open)
            print(f"⚠️ Errore DB chiavi: {e}")
            raise HTTPException(status_code=500, detail="Errore di validazione interno")

    # 4. INFERENZA INTELLIGENZA ARTIFICIALE
    testo_vettorizzato = vectorizer.transform([richiesta.testo])
    previsione = model.predict(testo_vettorizzato)

    if previsione[0] == 1:
        # 🔥 STRATEGIA VINCENTE: Deleghiamo il log a un task in background
        background_tasks.add_task(esegui_logging_supabase, richiesta.testo, chiave_pulita)
        
        # Rispondiamo IMMEDIATAMENTE allo scudo, azzerando i tempi di attesa del database
        return {"status": "403 Forbidden", "messaggio": "🚨 ATTACCO BLOCCATO"}
    
    else:
        return {"status": "200 OK", "messaggio": "✅ Accesso consentito"}

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=porta)