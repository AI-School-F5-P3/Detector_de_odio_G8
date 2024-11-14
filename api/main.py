from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
from typing import Dict, Union
import os


# Inicializar la aplicación FastAPI
app = FastAPI(title="Detector de Odio API",
              description="API para detectar mensajes de odio con threshold personalizado",
              version="1.0.0")

# Constantes
THRESHOLD = 0.59

try:
    # Cargar el modelo y el vectorizador
    # Obtener la ruta del directorio donde se encuentra el archivo main.py
    base_path = os.path.dirname(os.path.abspath(__file__))

    # Construir las rutas absolutas para los modelos y el vectorizador
    model_path = os.path.join(base_path, "..", "models", "ensemble_model.pkl")
    model = joblib.load(model_path)

    tfidf_path = os.path.join(base_path, "..", "models", "vectorizer_2.pkl")
    tfidf = joblib.load(tfidf_path)

    selector_path = os.path.join(base_path, "..", "models", "feature_selector.pkl")
    selector = joblib.load(selector_path)

except FileNotFoundError as e:
    raise HTTPException(status_code=500, detail=f"Error cargando modelos: {e}")

def get_hate_level(probability: float) -> str:
    """Determina el nivel de odio basado en la probabilidad."""
    if probability < THRESHOLD:
        return "Sin mensaje de odio detectado"
    else:
        return "Mensaje de odio detectado"

class PredictionRequest(BaseModel):
    text: str

class PredictionResponse(BaseModel):
    prediction: int
    probability: float
    hate_level: str
    details: Dict[str, Union[float, str]]

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        # Vectorizar el texto de entrada
        text_vectorized = tfidf.transform([request.text])
        
        # Aplicar selector de características si existe
        if selector:
            text_vectorized = selector.transform(text_vectorized)
        
        # Obtener probabilidades
        probabilities = model.predict_proba(text_vectorized)
        hate_prob = probabilities[0][1]  # Probabilidad de la clase positiva
        
        # Aplicar threshold
        prediction = 1 if hate_prob >= THRESHOLD else 0
        
        # Determinar nivel de odio
        hate_level = get_hate_level(hate_prob)
        
        # Preparar detalles adicionales
        details = {
            "threshold_used": THRESHOLD,
            "raw_probability": float(hate_prob),
            "confidence": f"{hate_prob * 100:.2f}%"
        }
        
        return PredictionResponse(
            prediction=prediction,
            probability=float(hate_prob),
            hate_level=hate_level,
            details=details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")

# Endpoint de información
@app.get("/info")
def get_info():
    return {
        "model_version": "1.0",
        "threshold": THRESHOLD,
        "hate_levels": {
            "Bajo": f"< {THRESHOLD}",
            "Moderado": f"{THRESHOLD} - 0.69",
            "Alto": "0.70 - 0.84",
            "Muy Alto": "≥ 0.85"
        }
    }