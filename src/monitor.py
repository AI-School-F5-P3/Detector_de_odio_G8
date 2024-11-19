# src/monitor.py
import googleapiclient.discovery
from typing import Optional
import os
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
