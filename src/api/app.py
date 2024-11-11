import streamlit as st
import requests

# URL de la API de FastAPI (actualízala si es necesario)
API_URL = "http://127.0.0.1:8000/predict"

st.title("Detector de Odio - Interfaz de Usuario")
st.write("Ingresa un mensaje para detectar si contiene contenido de odio:")

# Entrada de texto del usuario
message = st.text_input("Escribe tu mensaje aquí:")

# Botón para enviar
if st.button("Analizar"):
    if message:
        # Enviar solicitud a la API de FastAPI
        try:
            response = requests.post(API_URL, json={"text": message})
            if response.status_code == 200:
                # Mostrar la predicción recibida
                result = response.json().get("prediction")
                if result == 1:
                    st.write("Predicción: El mensaje contiene odio.")
                else:
                    st.write("Predicción: El mensaje no contiene odio.")
            else:
                st.write("Error en la predicción:", response.json().get("detail"))
        except Exception as e:
            st.write("Error de conexión con la API:", e)
    else:
        st.write("Por favor, ingresa un mensaje antes de analizar.")
