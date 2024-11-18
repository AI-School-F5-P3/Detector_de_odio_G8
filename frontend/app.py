import sys
import os 
import streamlit as st
import asyncio
import time
import httpx  # Usamos httpx para solicitudes asincrónicas
import requests
from typing import Dict
from datetime import datetime, timedelta
from frontend.utils import local_css, remote_css

# Añadimos el directorio `src` al sys.path
base_path = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(base_path, "..", "src")
static_path = os.path.join(os.path.dirname(__file__), 'static', 'style.css')

# Añadimos el directorio src al sys.path
sys.path.append(src_path)

# Ahora puedes importar el monitor sin problemas
from monitor import YouTubeMonitor
from chart import create_gauge_chart
from config import load_config

# Acceder a las variables de configuración
YOUTUBE_API_KEY = load_config("YOUTUBE_API_KEY")
API_URL = load_config("API_URL")
INFO_URL = load_config("INFO_URL")

# Símbolos de círculos
GREEN_CIRCLE = "\U0001F7E2"  # 🟢
RED_CIRCLE = "\U0001F534"    # 🔴

async def fetch_analysis(api_url: str, text: str) -> dict:
    """Realiza la solicitud a la API para analizar un comentario."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json={"text": text})
            if response.status_code == 200:
                return await response.json()  # Usa await aquí porque json() es asincrónico
            return {"error": f"Error en la API: {response.status_code}", "detail": response.text}
    except Exception as e:
        return {"error": "Error inesperado", "detail": str(e)}


# Actualización de analyze_comment
async def analyze_comment(text: str) -> Dict:
    """Analiza un comentario usando la API."""
    try:
        result = await fetch_analysis(API_URL, text)
        if not result:
            st.error("Error: No se pudo obtener la respuesta de la API.")
        return result
    except Exception as e:
        st.error(f"Error analizando comentario: {e}")
        return None


# # función asincrónica usando httpx
# async def analyze_comment(text: str) -> Dict:
#     """Analiza un comentario usando la API de detección de odio de forma asincrónica."""
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(API_URL, json={"text": text})
#             if response.status_code == 200:
#                 return response.json()
#             else:
#                 st.error(f"Error en API: {response.text}")
#                 return None
#     except Exception as e:
#         st.error(f"Error analizando comentario: {e}")
#         return None

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
            container = st.container(border=True)
            container.write(
                comment['text'],
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

async def wait_for_next_update(interval: int):
    """Esperar x segundos antes de la siguiente actualización."""
    await asyncio.sleep(interval)

async def process_comments(monitor: YouTubeMonitor, video_id: str, max_comments: int, processed_comments: set, all_comments: list, status_container, monitor_interval: int):
    """Obtiene y procesa los comentarios de YouTube y espera x segundos entre cada ciclo."""
    while True:
        # Obtener y mostrar los nuevos comentarios
        await get_new_comments(monitor, video_id, max_comments, processed_comments, all_comments, status_container)
        
        # Esperar x segundos antes de la siguiente actualización
        await wait_for_next_update(monitor_interval)

def main():
    # Cargar configuración y CSS
    local_css(static_path)

    # Incluye el enlace a la CDN de Material Icons
    remote_css("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css")

    st.title("🛡️ Detector de Odio")

    # Mantener un conjunto de comentarios procesados para evitar duplicados
    processed_comments = set()
    all_comments = []

    # Tabs para diferentes modos
    tab1, tab2 = st.tabs(["Análisis de Texto", "Análisis de Video"])

    with tab1:
        st.subheader("Análisis de Texto Individual")
        message = st.text_area("Ingresa el texto a analizar:", height=100, help="Escribe o pega el texto que deseas analizar")
        
        if st.button("Analizar texto", key="analizar_texto"):
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
                                fig = create_gauge_chart(analysis["probability"], analysis["details"]["threshold_used"])
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error(f"Error en la predicción: {response.json().get('detail', 'Error desconocido')}")
                    except Exception as e:
                        st.error(f"Error de conexión con la API: {e}")
            else:
                st.warning("⚠️ Por favor, ingresa un texto antes de analizar.")

    with tab2:
        st.subheader("Análisis de Comentarios de YouTube")
        video_url = st.text_input("URL del video de YouTube:", placeholder="https://www.youtube.com/watch?v=...")
        
        status_container = st.empty()

        # Configuración de monitoreo
        col1, col2 , col3 = st.columns(3)
        with col1:
            show_all_comments = st.radio("¿Ver todos los comentarios?", options=["Sí", "No"], index=1, horizontal=True)

        with col2:
            max_comments = st.number_input("Nº máximo de comentarios", min_value=1, max_value=10000, value=20) if show_all_comments == "No" else 10000

        with col3:
            monitor_interval = st.number_input("Intervalo de actualización (seg.)", min_value=10, max_value=30000, value=60)
        from streamlit_extras.stylable_container import stylable_container

        if st.button("Analizar comentarios", type="secondary", key="analizar_video"):
            if video_url:
                try:
                    # Inicializar monitor
                    api_key = os.getenv('YOUTUBE_API_KEY')
                    monitor = YouTubeMonitor(api_key)
                    video_id = monitor.extract_video_id(video_url)
                    
                    # Ejecutar el análisis asincrónicamente
                    asyncio.run(process_comments(monitor, video_id, max_comments, processed_comments, all_comments, status_container, monitor_interval))
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("⚠️ Por favor, ingresa una URL de YouTube válida.")

if __name__ == "__main__":
    main()