import sys
import os 
import streamlit as st
import asyncio
import time
import httpx
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
from frontend.utils import local_css, remote_css
from src.database import DatabaseManager

# Añadimos el directorio `src` al sys.path
base_path = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(base_path, "..", "src")
static_path = os.path.join(os.path.dirname(__file__), 'static', 'style.css')

# Añadimos el directorio src al sys.path
sys.path.append(src_path)

from src.monitor import YouTubeMonitor
from src.chart import create_gauge_chart
from src.config import load_config

# Acceder a las variables de configuración
YOUTUBE_API_KEY = load_config("YOUTUBE_API_KEY")
API_URL = load_config("API_URL")
INFO_URL = load_config("INFO_URL")

# Símbolos de círculos
GREEN_CIRCLE = "\U0001F7E2"  # 🟢
RED_CIRCLE = "\U0001F534"    # 🔴

async def fetch_analysis(api_url: str, text: str, model_type: str) -> dict:
    """Realiza la solicitud a la API para analizar un comentario."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json={"text": text, "model_type": model_type})
            if response.status_code == 200:
                return response.json()
            return {"error": f"Error en la API: {response.status_code}", "detail": response.text}
    except Exception as e:
        return {"error": "Error inesperado", "detail": str(e)}

async def analyze_comment(text: str, model_type: str) -> Optional[Dict]:
    """Analiza un comentario usando la API."""
    try:
        result = await fetch_analysis(API_URL, text, model_type)
        if not result:
            st.error("Error: No se pudo obtener la respuesta de la API.")
        return result
    except Exception as e:
        st.error(f"Error analizando comentario: {e}")
        return None

def display_comment_results(comment: Dict, analysis: Dict, index: int, video_id: str, db_manager: DatabaseManager):
    """Muestra los resultados del análisis de un comentario y guarda en la base de datos."""
    # Guardar el análisis en la base de datos según el tipo de modelo
    if analysis['details'].get('model_used') == 'transformer':
        db_manager.save_analysis(
            video_id=video_id,
            comment_id=comment['id'],
            transformer_result=analysis
        )
    else:  # traditional
        db_manager.save_analysis(
            video_id=video_id,
            comment_id=comment['id'],
            traditional_result=analysis
        )

    # Determinamos el color del círculo según el análisis
    if analysis['prediction'] == 1:
        comment_icon = RED_CIRCLE
    else:
        comment_icon = GREEN_CIRCLE

    # Fecha original en formato ISO 8601
    date_string = comment['date']

    # Convertir la cadena a un objeto datetime
    date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

    # Formatear la fecha al formato dd/mm/aaaa
    formatted_date = date_object.strftime("%d/%m/%Y - %H:%M")

    # Creamos un expander único para cada comentario con el ícono de color
    with st.expander(f"{comment_icon} Comentario de {comment['author']} - {formatted_date}"):
        col1, col2 = st.columns(2)
        
        with col1:
            unique_key_text = f"text_area_{comment['id']}_{index}_{time.time()}"
            container = st.container(border=True)
            container.write(
                comment['text'],
                key=unique_key_text
            )

            st.write(f"👍 Likes: {comment['likes']}")
            
            if analysis['prediction'] == 1:
                st.error("⚠️ Se ha detectado contenido de odio")
            else:
                st.success("✅ No se ha detectado contenido de odio")
            
            st.info(f"🤖 Modelo utilizado: {analysis['details'].get('model_used', 'transformer').title()}")
            
        with col2:
            fig = create_gauge_chart(
                analysis['probability'],
                analysis['details']['threshold_used']
            )
            
            unique_key_gauge = f"gauge_chart_{comment['id']}_{index}_{time.time()}"
            st.plotly_chart(fig, use_container_width=True, key=unique_key_gauge)

async def get_new_comments(monitor: YouTubeMonitor, video_id: str, max_comments: int, processed_comments: set, 
                          all_comments: list, status_container, model_type: str, db_manager: DatabaseManager):
    """Obtiene y procesa los comentarios más recientes de un video."""
    comments = monitor.get_comments(video_id, max_results=max_comments)
    
    if comments:
        status_container.write(f"### Analizados los {len(comments)} comentarios más recientes")
        status_container.write(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
                
        for i, comment in enumerate(comments):
            if comment['id'] not in processed_comments:
                analysis = await analyze_comment(comment['text'], model_type)
                if analysis:
                    processed_comments.add(comment['id'])
                    all_comments.insert(0, comment)
                    display_comment_results(comment, analysis, i, video_id, db_manager)
    else:
        status_container.write("No se encontraron comentarios.")

async def wait_for_next_update(interval: int):
    """Esperar x segundos antes de la siguiente actualización."""
    await asyncio.sleep(interval)

async def process_comments(monitor: YouTubeMonitor, video_id: str, max_comments: int, processed_comments: set, 
                         all_comments: list, status_container, monitor_interval: int, model_type: str, db_manager: DatabaseManager):
    """Procesa los comentarios periódicamente."""
    while True:
        await get_new_comments(monitor, video_id, max_comments, processed_comments, 
                             all_comments, status_container, model_type, db_manager)
        await wait_for_next_update(monitor_interval)

def main():
    # Cargar configuración y CSS
    local_css(static_path)
    remote_css("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css")

    st.title("🛡️ Detector de Odio")

    # Inicializar conexión a la base de datos
    db_manager = DatabaseManager()
    if not db_manager.connect():
        st.error("Error al conectar con la base de datos")
        return
    db_manager.create_tables()

    # Mantener un conjunto de comentarios procesados
    processed_comments = set()
    all_comments = []

    # Tabs para diferentes modos
    tab1, tab2, tab3 = st.tabs(["Análisis de Texto", "Análisis de Video", "Estadísticas"])

    with tab1:
        st.subheader("Análisis de Texto Individual")
        
        model_type = st.radio(
            "Selecciona el modelo a utilizar:",
            ["transformer", "traditional"],
            help="Transformer: Nuevo modelo basado en transformers\nTraditional: Modelo ensemble original"
        )
        
        message = st.text_area("Ingresa el texto a analizar:", height=100)
        
        if st.button("Analizar texto", key="analizar_texto"):
            if message:
                with st.spinner("Analizando texto..."):
                    try:
                        response = requests.post(
                            API_URL, 
                            json={"text": message, "model_type": model_type}
                        )
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

    with tab2:
        st.subheader("Análisis de Comentarios de YouTube")
        
        model_type_video = st.radio(
            "Selecciona el modelo a utilizar para el análisis de comentarios:",
            ["transformer", "traditional"],
            key="model_type_video",
            help="Transformer: Nuevo modelo basado en transformers\nTraditional: Modelo ensemble original"
        )
        
        video_url = st.text_input("URL del video de YouTube:", placeholder="https://www.youtube.com/watch?v=...")
        status_container = st.empty()

        col1, col2, col3 = st.columns(3)
        with col1:
            show_all_comments = st.radio("¿Ver todos los comentarios?", options=["Sí", "No"], index=1, horizontal=True)

        with col2:
            max_comments = st.number_input("Nº máximo de comentarios", min_value=1, max_value=10000, value=20) \
                if show_all_comments == "No" else 10000

        with col3:
            monitor_interval = st.number_input("Intervalo de actualización (seg.)", min_value=10, max_value=30000, value=60)

        if st.button("Analizar comentarios", type="secondary", key="analizar_video"):
            if video_url:
                try:
                    api_key = os.getenv('YOUTUBE_API_KEY')
                    monitor = YouTubeMonitor(api_key)
                    video_id = monitor.extract_video_id(video_url)
                    
                    asyncio.run(process_comments(
                        monitor, video_id, max_comments, processed_comments,
                        all_comments, status_container, monitor_interval, 
                        model_type_video, db_manager
                    ))
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("⚠️ Por favor, ingresa una URL de YouTube válida.")

    with tab3:
        st.subheader("Estadísticas de Análisis")
        video_url_stats = st.text_input(
            "URL del video para estadísticas:",
            placeholder="https://www.youtube.com/watch?v=...",
            key="video_url_stats"
        )
        
        if st.button("Ver estadísticas", key="ver_stats"):
            if video_url_stats:
                try:
                    video_id = YouTubeMonitor(YOUTUBE_API_KEY).extract_video_id(video_url_stats)
                    stats = db_manager.get_video_statistics(video_id)
                    if stats:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Comentarios", stats['total_comments'])
                        with col2:
                            st.metric("Hate (Traditional)", stats['traditional_hate_count'])
                        with col3:
                            st.metric("Hate (Transformer)", stats['transformer_hate_count'])
                    else:
                        st.warning("No hay datos para este video")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Cerrar conexión a la base de datos al finalizar
    db_manager.disconnect()

if __name__ == "__main__":
    main()