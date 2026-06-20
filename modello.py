dati_X = [
    "cerca scarpe da ginnastica",
    "SELECT * FROM passwords",
    "login utente mario",
    "alert('hacked')",
    "leggi articolo di blog",
    "DROP TABLE users",
]
etichette =[0,1,0,1,0,1]
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
vectorizer = CountVectorizer()
# Calcola il vocabolario e converte il testo in una matrice
X = vectorizer.fit_transform(dati_X)

# Visualizza le parole del vocabolario individuate
print(vectorizer.get_feature_names_out())

# Add and train a Logistic Regression model
model = LogisticRegression()
model.fit(X, etichette)
#print("Model trained. Classes:", model.classes_)
preds = model.predict(X)
#print("Predictions:", preds)

nuova_richiesta = ["DROP DATABASE;"]

# 2. Traduciamo in numeri SENZA fargli dimenticare il passato (usiamo solo .transform)
nuovo_X = vectorizer.transform(nuova_richiesta)

# 3. Facciamo la previsione
previsione = model.predict(nuovo_X)
if previsione[0] == 1:
    print("Attenzione: possibile attacco SQL rilevato!")    

import joblib

# Salviamo fisicamente il modello matematico
joblib.dump(model, 'modello_ai.pkl')

# Salviamo fisicamente il vocabolario (ci serve per le frasi future)
joblib.dump(vectorizer, 'vectorizer.pkl')

print("Cervello congelato e salvato con successo!")