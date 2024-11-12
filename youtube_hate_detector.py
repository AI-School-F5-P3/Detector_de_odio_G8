import os
import googleapiclient.discovery
from joblib import load
import pandas as pd
import logging
from datetime import datetime
from dotenv import load_dotenv
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, f_classif


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeHateDetector:
    def __init__(self, api_key=None, model_path=None):
        """
        Inicializa el detector de mensajes de odio en YouTube.
        """
        # Intentar cargar API key desde variable de entorno si no se proporciona
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("No se proporcionó API key de YouTube.")

        # Intentar cargar modelo desde la ruta proporcionada o la ruta por defecto
        self.model_path = model_path or os.getenv('MODEL_PATH', 'model/ensemble_model_complete.joblib')
        
        # Inicializar la API de YouTube
        try:
            self.youtube = googleapiclient.discovery.build(
                "youtube", "v3", developerKey=self.api_key
            )
            logger.info("Conexión con YouTube API establecida correctamente")
        except Exception as e:
            logger.error(f"Error al conectar con YouTube API: {str(e)}")
            raise
        
        # Cargar el modelo, vectorizador, selector y threshold desde el archivo
        self._load_model()
        
    def _load_model(self):
        """Carga el modelo, vectorizador, selector y threshold desde el archivo joblib"""
        logger.info(f"Cargando modelo desde: {self.model_path}")
        try:
            # Cargar el diccionario con los componentes
            loaded_data = load(self.model_path)
            self.model = loaded_data['model']
            self.vectorizer = loaded_data['vectorizer']  # El vectorizador debe estar ya ajustado
            self.selector = loaded_data['selector']
            self.threshold = loaded_data['threshold']  # Cargar el umbral
            logger.info("Modelo, vectorizador, selector y umbral cargados correctamente")
        except Exception as e:
            logger.error(f"Error al cargar el modelo: {str(e)}")
            raise

    def preprocess_text(self, text):
        """
        Preprocesa el texto del comentario (opcional, puedes añadir más procesamiento aquí).
        """
        return text.lower()

    def analyze_comments(self, comments):
        """
        Analiza los comentarios usando el modelo entrenado.
        
        Parámetros:
        - comments (list): Lista de diccionarios con la estructura {"text": str, "date": str}

        Retorna:
        - pd.DataFrame: DataFrame con los resultados de la predicción.
        """
        if not comments:
            logger.warning("No hay comentarios para analizar")
            return pd.DataFrame()

        df = pd.DataFrame(comments)
        
        try:
            # Preprocesar los textos
            logger.info("Preprocesando comentarios...")
            texts = [self.preprocess_text(text) for text in df['text']]
            
            # Vectorizar los textos (mantener 1859 características)
            logger.info("Vectorizando textos...")
            X = self.vectorizer.transform(texts)
            
            # Asegurarse de que las características tengan el número esperado
            if X.shape[1] != 1859:
                logger.info(f"Reajustando el número de características: {X.shape[1]} -> 1859")
                # Si el número de características es diferente, ajustamos las características
                # Usamos SelectKBest para seleccionar las 1859 mejores características
                kbest = SelectKBest(f_classif, k=1859)
                X = kbest.fit_transform(X, [0] * X.shape[0])  # Dummy target, no necesario si solo queremos las features
                logger.info(f"Características ajustadas a 1859.")
            
            # Reducir dimensionalidad usando el selector guardado
            X = self.selector.transform(X)
            
            # Realizar predicciones
            logger.info("Realizando predicciones...")
            probabilities = self.model.predict_proba(X)
            
            # Obtener la probabilidad de toxicidad (segunda columna)
            toxic_probabilities = probabilities[:, 1]
            
            # Clasificar si es tóxico o no en función del umbral
            is_toxic = (toxic_probabilities > self.threshold).astype(int)
            
            # Añadir resultados al DataFrame
            df['is_toxic'] = is_toxic
            df['toxic_probability'] = toxic_probabilities
            
            # Convertir fechas a formato datetime
            df['date'] = pd.to_datetime(df['date'])
            
        except Exception as e:
            logger.error(f"Error durante el análisis: {str(e)}")
            raise
        
        return df


    def fetch_comments(self, video_id, max_results=100):
        """
        Obtiene comentarios de un video de YouTube.
        
        Parámetros:
        - video_id (str): ID del video de YouTube.
        - max_results (int): Número máximo de comentarios a recuperar.

        Retorna:
        - list: Lista de comentarios en forma de diccionarios.
        """
        try:
            logger.info(f"Obteniendo comentarios para el video {video_id}")
            response = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_results, 100),
                textFormat="plainText"
            ).execute()

            comments = []
            for item in response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "text": comment["textDisplay"],
                    "date": comment["publishedAt"]
                })
            logger.info(f"Se obtuvieron {len(comments)} comentarios")
            return comments
        except Exception as e:
            logger.error(f"Error al obtener comentarios: {str(e)}")
            raise

    def extract_video_id(self, url):
        """
        Extrae el ID del video desde la URL de YouTube.
        
        Parámetros:
        - url (str): URL del video de YouTube.

        Retorna:
        - str: ID del video extraído de la URL.
        """
        video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
        if video_id_match:
            return video_id_match.group(1)
        else:
            raise ValueError("No se pudo extraer el ID del video de la URL proporcionada.")

def main():
    # Cargar variables de entorno desde .env
    load_dotenv()
    
    try:
        # Crear instancia del detector
        logger.info("Iniciando detector de odio en YouTube...")
        detector = YouTubeHateDetector()
        
        # Solicitar URL del video
        video_url = input("Ingrese la URL del video de YouTube: ")
        video_id = detector.extract_video_id(video_url)
        
        # Obtener y analizar comentarios
        logger.info("Obteniendo comentarios para el video...")
        comments = detector.fetch_comments(video_id)
        
        if not comments:
            print("No se pudieron obtener comentarios del video.")
            return
        
        # Analizar comentarios
        logger.info("Analizando comentarios...")
        results_df = detector.analyze_comments(comments)
        
        # Generar y guardar reporte
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"reporte_toxicidad_{timestamp}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\nReporte generado: {output_file}")
        
    except Exception as e:
        logger.error(f"Error en la ejecución: {str(e)}")
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()
