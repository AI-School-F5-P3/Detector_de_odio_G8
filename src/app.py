import streamlit as st
import requests
import pandas as pd
from typing import Dict
import plotly.graph_objects as go

# Configuración
API_URL = "http://127.0.0.1:8000/predict"
INFO_URL = "http://127.0.0.1:8000/info"

# Configuración de la página
st.set_page_config(
    page_title="Detector de Odio",
    page_icon="🛡️",
    layout="wide"
)

def create_gauge_chart(probability: float, threshold: float) -> go.Figure:
    """Crea un gráfico de gauge para visualizar la probabilidad."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = probability * 100,
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, threshold * 100], 'color': "lightgray"},
                {'range': [threshold * 100, 100], 'color': "rgb(250, 200, 200)"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': threshold * 100
            }
        },
        title = {'text': "Probabilidad de Odio (%)"}
    ))
    
    fig.update_layout(height=250)
    return fig

def display_results(response: Dict):
    """Muestra los resultados del análisis."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Resultado del Análisis")
        
        # Mostrar predicción con formato
        if response["prediction"] == 1:
            st.error("⚠️ Se ha detectado contenido de odio")
        else:
            st.success("✅ No se ha detectado contenido de odio")
        
        # Mostrar nivel de odio
        st.info(f"Nivel de Odio: {response['hate_level']}")
        
        # Mostrar detalles adicionales
        st.write("Detalles:")
        for key, value in response["details"].items():
            st.write(f"- {key}: {value}")
    
    with col2:
        # Mostrar gráfico de gauge
        fig = create_gauge_chart(
            response["probability"],
            response["details"]["threshold_used"]
        )
        st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🛡️ Detector de Odio - Análisis de Texto")
    
    # Mostrar información sobre los niveles de odio
    with st.expander("ℹ️ Información sobre niveles de odio"):
        try:
            info_response = requests.get(INFO_URL)
            if info_response.status_code == 200:
                info = info_response.json()
                st.write("Niveles de clasificación:")
                for level, range_info in info["hate_levels"].items():
                    st.write(f"- **{level}**: {range_info}")
        except:
            st.warning("No se pudo cargar la información de niveles")
    
    # Entrada de texto del usuario
    message = st.text_area(
        "Ingresa el texto a analizar:",
        height=100,
        help="Escribe o pega el texto que deseas analizar"
    )
    
    # Botón para enviar
    if st.button("🔍 Analizar Texto", type="primary"):
        if message:
            with st.spinner("Analizando texto..."):
                try:
                    response = requests.post(API_URL, json={"text": message})
                    if response.status_code == 200:
                        display_results(response.json())
                    else:
                        st.error(f"Error en la predicción: {response.json().get('detail', 'Error desconocido')}")
                except Exception as e:
                    st.error(f"Error de conexión con la API: {e}")
        else:
            st.warning("⚠️ Por favor, ingresa un texto antes de analizar.")
    
    # Información adicional
    st.markdown("---")
    st.markdown("""
        ### Acerca del detector
        Este detector utiliza modelos de aprendizaje automático para identificar posible contenido de odio en textos.
        La evaluación se basa en múltiples factores y proporciona una probabilidad y nivel de confianza.
        
        **Nota**: Esta herramienta es solo para fines de análisis y debe usarse como apoyo, no como única fuente de decisión.
    """)

if __name__ == "__main__":
    main()