import streamlit as st
import requests
import pandas as pd
from typing import Dict, Optional
import plotly.graph_objects as go
from datetime import datetime, timedelta
import asyncio
import googleapiclient.discovery
import os
from dotenv import load_dotenv
import logging
import time
import httpx  # Usamos httpx para solicitudes asincrónicas

# Configuración
API_URL = "http://127.0.0.1:8000/predict"
INFO_URL = "http://127.0.0.1:8000/info"

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Símbolos de círculos
GREEN_CIRCLE = "\U0001F7E2"  # 🟢
RED_CIRCLE = "\U0001F534"    # 🔴

class YouTubeMonitor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key no encontrada")
            
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3",
            developerKey=self.api_key,
            cache_discovery=False
        )
        
    def extract_video_id(self, url: str) -> str:
        """Extrae el ID del video desde una URL de YouTube."""
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        raise ValueError("URL de YouTube inválida")

    def get_comments(self, video_id: str, max_results: int = 100) -> list:
        """Obtiene los comentarios más recientes de un video."""
        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                textFormat="plainText",
                order="time",
                maxResults=max_results
            )
            
            response = request.execute()
            comments = []
            
            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'id': item['id'],
                    'text': comment['textDisplay'],
                    'author': comment['authorDisplayName'],
                    'date': comment['publishedAt'],
                    'likes': comment['likeCount']
                })
                
            return comments
        except Exception as e:
            logger.error(f"Error obteniendo comentarios: {e}")
            return []

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

# Convertir analyze_comment en una función asincrónica usando httpx
async def analyze_comment(text: str) -> Dict:
    """Analiza un comentario usando la API de detección de odio de forma asincrónica."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, json={"text": text})
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Error en API: {response.text}")
                return None
    except Exception as e:
        st.error(f"Error analizando comentario: {e}")
        return None

import time

def display_comment_results(comment: Dict, analysis: Dict, index: int):
    """Muestra los resultados del análisis de un comentario dentro de un desplegable (st.expander)."""
    # Determinamos el color del círculo según el análisis
    if analysis['prediction'] == 1:
        comment_icon = RED_CIRCLE  # Comentario de odio
    else:
        comment_icon = GREEN_CIRCLE  # Comentario sin odio

    # Creamos un expander único para cada comentario con el ícono de color
    with st.expander(f"{comment_icon} Comentario de {comment['author']} - {comment['date']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Crear un key único para el text_area
            unique_key_text = f"text_area_{comment['id']}_{index}_{time.time()}"
            st.text_area(
                "Texto:", 
                comment['text'], 
                disabled=True, 
                key=unique_key_text  # Unique key using comment id, index, and timestamp
            )
            st.write(f"👍 Likes: {comment['likes']}")
            
            if analysis['prediction'] == 1:
                st.error("⚠️ Se ha detectado contenido de odio")
            else:
                st.success("✅ No se ha detectado contenido de odio")
            
        with col2:
            fig = create_gauge_chart(
                analysis['probability'],
                analysis['details']['threshold_used']
            )
            
            # Crear un key único para el gráfico
            unique_key_gauge = f"gauge_chart_{comment['id']}_{index}_{time.time()}"
            st.plotly_chart(fig, use_container_width=True, key=unique_key_gauge)

async def get_new_comments(monitor: YouTubeMonitor, video_id: str, max_comments: int, processed_comments: set, all_comments: list, status_container):
    """Obtiene y procesa los comentarios más recientes de un video."""
    comments = monitor.get_comments(video_id, max_results=max_comments)
    
    if comments:
        status_container.write(f"### Analizados los {len(comments)} comentarios más recientes")
        status_container.write(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
                
        # Analizamos cada comentario, solo si no ha sido procesado
        for i, comment in enumerate(comments):
            # Si el comentario ya fue procesado, lo ignoramos
            if comment['id'] not in processed_comments:
                analysis = await analyze_comment(comment['text'])
                if analysis:
                    processed_comments.add(comment['id'])  # Marcar este comentario como procesado
                    # Insertar comentario nuevo al principio de la lista
                    all_comments.insert(0, comment)
                    display_comment_results(comment, analysis, i)  # Pasamos `i` como índice
    else:
        status_container.write("No se encontraron comentarios.")
    
async def wait_for_next_update():
    """Esperar 60 segundos antes de la siguiente actualización."""
    await asyncio.sleep(10)

async def process_comments(monitor: YouTubeMonitor, video_id: str, max_comments: int, processed_comments: set, all_comments: list, status_container):
    """Obtiene y procesa los comentarios de YouTube y espera 60 segundos entre cada ciclo."""
    while True:
        # Obtener y mostrar los nuevos comentarios
        await get_new_comments(monitor, video_id, max_comments, processed_comments, all_comments, status_container)
        
        # Esperar 60 segundos antes de la siguiente actualización
        await wait_for_next_update()

def main():
    st.set_page_config(
        page_title="Detector de Odio YouTube",
        page_icon="🛡️",
        layout="wide"
    )
    
    st.title("🛡️ Detector de Odio - Análisis de YouTube")
    
    # Mantener un conjunto de comentarios procesados para evitar duplicados
    processed_comments = set()
    
    # Lista de todos los comentarios procesados
    all_comments = []

    # Tabs para diferentes modos
    tab1, tab2 = st.tabs(["Análisis de Video", "Análisis de Texto"])
    
    with tab1:
        st.subheader("Análisis de Comentarios de YouTube")
        
        # Input para URL de YouTube
        video_url = st.text_input(
            "URL del video de YouTube:",
            placeholder="https://www.youtube.com/watch?v=..."
        )
        
        # Crear un contenedor vacío para el texto y actualizarlo dinámicamente
        status_container = st.empty()

        # Configuración de monitoreo
        col1, col2 = st.columns(2)
        with col1:
            # Nuevo selector para mostrar todos los comentarios o limitar a una cantidad
            show_all_comments = st.radio(
                "¿Ver todos los comentarios?",
                options=["Sí", "No"],
                index=1  # "No" por defecto
            )
            
            if show_all_comments == "No":
                max_comments = st.number_input(
                    "Número máximo de comentarios a analizar:",
                    min_value=1,
                    max_value=10000,
                    value=20
                )
            else:
                max_comments = 10000  # Mostrar todos los comentarios

        with col2:
            monitor_interval = st.number_input(
                "Intervalo de actualización (segundos):",
                min_value=10,
                max_value=30000,
                value=60
            )
        
        if st.button("🔍 Analizar Comentarios", type="primary"):
            if video_url:
                try:
                    # Inicializar monitor
                    api_key = os.getenv('YOUTUBE_API_KEY')
                    monitor = YouTubeMonitor(api_key)
                    video_id = monitor.extract_video_id(video_url)
                    
                    # Ejecutar el análisis asincrónicamente
                    asyncio.run(process_comments(monitor, video_id, max_comments, processed_comments, all_comments, status_container))
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("⚠️ Por favor, ingresa una URL de YouTube válida.")

    with tab2:
        st.subheader("Análisis de Texto Individual")
        
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
                            analysis = response.json()
                            col1, col2 = st.columns(2)
                            

                            with col1:
                                st.subheader("Resultado del Análisis")
                                

                                if analysis["prediction"] == 1:
                                    st.error("⚠️ Se ha detectado contenido de odio")
                                else:
                                    st.success("✅ No se ha detectado contenido de odio")
                                                                
                                st.write("Detalles:")
                                for key, value in analysis["details"].items():
                                    st.write(f"- {key}: {value}")
                            

                            with col2:
                                fig = create_gauge_chart(
                                    analysis["probability"],
                                    analysis["details"]["threshold_used"]
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error(f"Error en la predicción: {response.json().get('detail', 'Error desconocido')}")
                    except Exception as e:
                        st.error(f"Error de conexión con la API: {e}")
            else:
                st.warning("⚠️ Por favor, ingresa un texto antes de analizar.")

if __name__ == "__main__":
    main()
