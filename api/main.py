from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
from typing import Dict, Union
import os
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

# Inicializar la aplicación FastAPI
app = FastAPI(title="Detector de Odio API",
              description="API para detectar mensajes de odio con threshold personalizado",
              version="2.0.0")

# Constantes
THRESHOLD = 0.59


# Paths
base_path = os.path.dirname(os.path.abspath(__file__))
models_path = os.path.join(base_path, "..", "models")

try:
    # Cargar el modelo tradicional y sus componentes
    model_path = os.path.join(models_path, "ensemble_model.pkl")
    tfidf_path = os.path.join(models_path, "vectorizer_2.pkl")
    selector_path = os.path.join(models_path, "feature_selector.pkl")
    
    traditional_model = joblib.load(model_path)
    tfidf = joblib.load(tfidf_path)
    selector = joblib.load(selector_path)
    
    # Cargar el modelo transformer
    transformer_path = os.path.join(models_path)
    transformer_model = AutoModelForSequenceClassification.from_pretrained(transformer_path)
    tokenizer = AutoTokenizer.from_pretrained(transformer_path)
    
    # Mover el modelo a GPU si está disponible
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    transformer_model = transformer_model.to(device)
    transformer_model.eval()  # Establecer el modelo en modo evaluación

except FileNotFoundError as e:
    raise HTTPException(status_code=500, detail=f"Error cargando modelos: {e}")

def get_hate_level(probability: float) -> str:
    """Determina el nivel de odio basado en la probabilidad."""
    if probability < THRESHOLD:
        return "Sin mensaje de odio detectado"
    else:
        return "Mensaje de odio detectado"

def get_transformer_prediction(text: str) -> tuple:
    """Obtiene la predicción usando el modelo transformer."""
    try:
        # Tokenizar el texto
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(device)
        
        # Obtener predicción
        with torch.no_grad():
            outputs = transformer_model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
            
        # Obtener probabilidad de la clase positiva
        hate_prob = probabilities[0][1].item()
        prediction = 1 if hate_prob >= THRESHOLD else 0
        
        return prediction, hate_prob
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción transformer: {str(e)}")

def get_traditional_prediction(text: str) -> tuple:
    """Obtiene la predicción usando el modelo tradicional."""
    try:
        text_vectorized = tfidf.transform([text])
        if selector:
            text_vectorized = selector.transform(text_vectorized)
            
        probabilities = traditional_model.predict_proba(text_vectorized)
        hate_prob = probabilities[0][1]
        prediction = 1 if hate_prob >= THRESHOLD else 0
        
        return prediction, hate_prob
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción tradicional: {str(e)}")

class PredictionRequest(BaseModel):
    text: str
    model_type: str = "transformer"  # "transformer" o "traditional"

class PredictionResponse(BaseModel):
    prediction: int
    probability: float
    hate_level: str
    details: Dict[str, Union[float, str]]

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        # Seleccionar el modelo según el tipo especificado
        if request.model_type.lower() == "transformer":
            prediction, hate_prob = get_transformer_prediction(request.text)
        else:
            prediction, hate_prob = get_traditional_prediction(request.text)
        
        # Determinar nivel de odio
        hate_level = get_hate_level(hate_prob)
        
        # Preparar detalles adicionales
        details = {
            "threshold_used": THRESHOLD,
            "raw_probability": float(hate_prob),
            "confidence": f"{hate_prob * 100:.2f}%",
            "model_used": request.model_type
        }
        
        return PredictionResponse(
            prediction=prediction,
            probability=float(hate_prob),
            hate_level=hate_level,
            details=details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la predicción: {str(e)}")

@app.get("/info")
def get_info():
    return {
        "model_version": "2.0",
        "available_models": ["transformer", "traditional"],
        "threshold": THRESHOLD,
        "hate_levels": {
            "Bajo": f"< {THRESHOLD}",
            "Moderado": f"{THRESHOLD} - 0.69",
            "Alto": "0.70 - 0.84",
            "Muy Alto": "≥ 0.85"
        }
    }