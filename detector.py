import googleapiclient.discovery
import joblib
import pandas as pd
from datetime import datetime
import numpy as np
from typing import List, Dict, Tuple
import logging

class YouTubeHateDetector:
    def __init__(self, api_key: str, threshold: float = 0.59):
        """
        Inicializa el detector de mensajes de odio para YouTube.
        
        Args:
            api_key (str): API key de YouTube Data API v3
            threshold (float): Umbral de probabilidad para clasificar mensaje como odio (default: 0.59)
        """
        self.threshold = threshold
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Inicializando detector con threshold={threshold}")
        
        # Cargar modelos pre-entrenados
        try:
            self.vectorizer = joblib.load('vectorizer_2.pkl')
            self.selector = joblib.load('feature_selector.pkl')
            self.model = joblib.load('ensemble_model.pkl')
            self.logger.info("Modelos cargados exitosamente")
        except Exception as e:
            self.logger.error(f"Error al cargar los modelos: {e}")
            raise
        
        # Inicializar API de YouTube
        try:
            self.youtube = googleapiclient.discovery.build(
                "youtube", "v3", developerKey=api_key
            )
            self.logger.info("API de YouTube inicializada correctamente")
        except Exception as e:
            self.logger.error(f"Error al inicializar YouTube API: {e}")
            raise

    def extract_video_id(self, url: str) -> str:
        """
        Extrae el ID del video de una URL de YouTube.
        
        Args:
            url (str): URL del video de YouTube
            
        Returns:
            str: ID del video
        """
        if "youtube.com/watch?v=" in url:
            return url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        else:
            raise ValueError("URL de YouTube no válida")

    def get_video_comments(self, video_id: str, max_results: int = 100) -> List[Dict]:
        """
        Obtiene los comentarios de un video de YouTube.
        
        Args:
            video_id (str): ID del video de YouTube
            max_results (int): Número máximo de comentarios a obtener
            
        Returns:
            List[Dict]: Lista de comentarios con su información
        """
        try:
            comments = []
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_results, 100),
                textFormat="plainText"
            )
            
            while request and len(comments) < max_results:
                response = request.execute()
                
                for item in response["items"]:
                    comment = item["snippet"]["topLevelComment"]["snippet"]
                    comments.append({
                        'text': comment["textDisplay"],
                        'author': comment["authorDisplayName"],
                        'date': comment["publishedAt"],
                        'likes': comment["likeCount"]
                    })
                
                request = self.youtube.commentThreads().list_next(request, response)
                
            self.logger.info(f"Obtenidos {len(comments)} comentarios")
            return comments
            
        except Exception as e:
            self.logger.error(f"Error al obtener comentarios: {e}")
            raise

    def predict_hate_speech(self, texts: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predice si los textos contienen mensajes de odio usando el threshold definido.
        
        Args:
            texts (List[str]): Lista de textos a analizar
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Predicciones y probabilidades
        """
        try:
            # Vectorizar textos
            X = self.vectorizer.transform(texts)
            
            # Seleccionar características
            X_selected = self.selector.transform(X)
            
            # Obtener probabilidades
            probabilities = self.model.predict_proba(X_selected)
            
            # Aplicar threshold personalizado
            predictions = (probabilities[:, 1] >= self.threshold).astype(int)
            
            return predictions, probabilities
            
        except Exception as e:
            self.logger.error(f"Error en la predicción: {e}")
            raise

    def get_hate_level(self, probability: float) -> str:
        """
        Determina el nivel de odio basado en la probabilidad.
        
        Args:
            probability (float): Probabilidad de mensaje de odio
            
        Returns:
            str: Nivel de odio (Bajo, Moderado, Alto, Muy Alto)
        """
        if probability < self.threshold:
            return "Bajo"
        elif probability < 0.7:
            return "Moderado"
        elif probability < 0.85:
            return "Alto"
        else:
            return "Muy Alto"

    def analyze_video_comments(self, video_url: str, max_comments: int = 100) -> pd.DataFrame:
        """
        Analiza los comentarios de un video en busca de mensajes de odio.
        
        Args:
            video_url (str): URL del video de YouTube
            max_comments (int): Número máximo de comentarios a analizar
            
        Returns:
            pd.DataFrame: DataFrame con el análisis de los comentarios
        """
        try:
            # Extraer ID del video
            video_id = self.extract_video_id(video_url)
            
            # Obtener comentarios
            comments = self.get_video_comments(video_id, max_comments)
            
            # Preparar datos para análisis
            texts = [comment['text'] for comment in comments]
            
            # Realizar predicciones
            predictions, probabilities = self.predict_hate_speech(texts)
            
            # Crear DataFrame con resultados
            results_df = pd.DataFrame(comments)
            results_df['hate_speech'] = predictions
            results_df['hate_probability'] = probabilities[:, 1]
            
            # Añadir nivel de odio
            results_df['hate_level'] = results_df['hate_probability'].apply(self.get_hate_level)
            
            # Ordenar por probabilidad de discurso de odio
            results_df = results_df.sort_values('hate_probability', ascending=False)
            
            # Convertir fechas a formato datetime
            results_df['date'] = pd.to_datetime(results_df['date'])
            
            # Calcular estadísticas
            total_comments = len(results_df)
            hate_comments = sum(predictions)
            hate_percentage = (hate_comments/total_comments)*100
            
            # Estadísticas por nivel
            level_stats = results_df['hate_level'].value_counts()
            
            self.logger.info(f"""
                Análisis completado:
                - Total comentarios analizados: {total_comments}
                - Comentarios clasificados como odio (>={self.threshold}): {hate_comments}
                - Porcentaje de mensajes de odio: {hate_percentage:.2f}%
                
                Distribución por niveles:
                {level_stats.to_string()}
            """)
            
            return results_df
            
        except Exception as e:
            self.logger.error(f"Error en el análisis del video: {e}")
            raise

def main():
    # Ejemplo de uso
    API_KEY = "AIzaSyBrSGVkVLUS1WFOvRDg_FM4SZzNtCrtXVI"  # Reemplazar con tu API key
    
    try:
        # Inicializar detector con threshold personalizado
        detector = YouTubeHateDetector(API_KEY, threshold=0.59)
        
        # URL de ejemplo
        video_url = "https://www.youtube.com/watch?v=a5uQMwRMHcs"
        
        # Realizar análisis
        results = detector.analyze_video_comments(video_url, max_comments=10000)
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results.to_csv(f'analisis_comentarios_{timestamp}.csv', index=False)
        
        # Mostrar resumen de comentarios problemáticos
        print("\nComentarios con mayor probabilidad de contener discurso de odio:")
        print(results[['text', 'hate_probability', 'hate_level', 'author']]
              .head()
              .to_string(index=False))
        
        # Mostrar estadísticas por nivel
        print("\nDistribución por niveles de odio:")
        print(results['hate_level'].value_counts().to_string())
        
    except Exception as e:
        print(f"Error en la ejecución: {e}")

if __name__ == "__main__":
    main()