from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np

# Inicializar la aplicación FastAPI
app = FastAPI()

try:
    # Cargar el modelo y el vectorizador
    model = joblib.load("models/ensemble_model_complete.joblib")
    tfidf = joblib.load("models/tfidf_vectorizer.joblib")
except FileNotFoundError as e:
    raise HTTPException(status_code=500, detail=f"File not found: {e}")

# Definir la estructura de los datos de entrada
class PredictionRequest(BaseModel):
    text: str

# Endpoint de predicción
@app.post("/predict")
def predict(request: PredictionRequest):
    try:
        # Vectorizar el texto de entrada
        text_vectorized = tfidf.transform([request.text])
        prediction = model.predict(text_vectorized)
        return {"prediction": int(prediction[0])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
