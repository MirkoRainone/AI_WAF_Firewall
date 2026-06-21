import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

print("⏳ 1. Lettura del dataset in corso...")
# Usiamo il CSV sintetico che hai scaricato prima per fare il test
df = pd.read_csv("dataset_waf.csv")

# Pulizia di base: rimuoviamo eventuali righe vuote o corrotte
df = df.dropna()
X = df['testo'].astype(str)
y = df['etichetta'].astype(int)

print("🔪 2. Divisione dei dati (80% Studio, 20% Esame a sorpresa)...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("🧮 3. Traduzione avanzata (Analisi dei frammenti di codice)...")
# LA MAGIA È QUI: analyzer='char_wb' e ngram_range=(2, 5)
# Insegna all'IA a cercare sequenze di simboli, non solo parole intere.
vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5))
X_train_numeri = vectorizer.fit_transform(X_train)
X_test_numeri = vectorizer.transform(X_test)

print("🧠 4. Addestramento dell'Intelligenza Artificiale...")
modello = LogisticRegression(max_iter=1000)
modello.fit(X_train_numeri, y_train)

print("📊 5. Esame Finale (Valutazione delle performance):")
# Facciamo fare all'IA le previsioni sul 20% dei dati che non ha mai visto
previsioni = modello.predict(X_test_numeri)
print(classification_report(y_test, previsioni, target_names=['0 (Utenti Normali)', '1 (Hacker)']))

print("📦 6. Salvataggio del nuovo cervello...")
joblib.dump(vectorizer, 'traduttore_waf.pkl')
joblib.dump(modello, 'cervello_waf.pkl')

print("🎉 FATTO! Pronti per essere caricati su Render.")