# src/database.py
import os
import psycopg2
from psycopg2.extras import DictCursor
from typing import Optional, Dict
from src.config import load_config

class DatabaseManager:
    def __init__(self):
        """Inicializa la conexión a la base de datos usando las variables de configuración."""
        self.db_params = {
            'dbname': load_config('DB_NAME'),
            'user': load_config('DB_USER'),
            'password': load_config('DB_PASSWORD'),
            'host': load_config('DB_HOST'),
            'port': load_config('DB_PORT')
        }
        self.connection = None
        self.cursor = None

    def connect(self):
        """Establece la conexión con la base de datos."""
        try:
            self.connection = psycopg2.connect(**self.db_params)
            self.cursor = self.connection.cursor(cursor_factory=DictCursor)
            return True
        except psycopg2.Error as e:
            print(f"Error conectando a la base de datos: {e}")
            return False

    def disconnect(self):
        """Cierra la conexión con la base de datos."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def create_tables(self):
        """Crea la tabla de análisis si no existe."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS comment_analysis (
            id SERIAL PRIMARY KEY,
            video_id VARCHAR(50) NOT NULL,
            comment_id VARCHAR(100) NOT NULL,
            traditional_hate SMALLINT NOT NULL,
            transformer_hate SMALLINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(video_id, comment_id)
        );
        """
        try:
            self.cursor.execute(create_table_query)
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error creando la tabla: {e}")
            self.connection.rollback()
            return False

    def save_analysis(self, video_id: str, comment_id: str, 
                     traditional_result: Optional[Dict] = None,
                     transformer_result: Optional[Dict] = None) -> bool:
        """
        Guarda los resultados del análisis en la base de datos.
        
        Args:
            video_id: ID del video de YouTube
            comment_id: ID del comentario
            traditional_result: Resultado del modelo tradicional (opcional)
            transformer_result: Resultado del modelo transformer (opcional)
        
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        traditional_hate = traditional_result['prediction'] if traditional_result else None
        transformer_hate = transformer_result['prediction'] if transformer_result else None

        insert_query = """
        INSERT INTO comment_analysis (video_id, comment_id, traditional_hate, transformer_hate)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (video_id, comment_id) DO UPDATE
        SET traditional_hate = EXCLUDED.traditional_hate,
            transformer_hate = EXCLUDED.transformer_hate;
        """
        
        try:
            self.cursor.execute(insert_query, 
                              (video_id, comment_id, traditional_hate, transformer_hate))
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error guardando el análisis: {e}")
            self.connection.rollback()
            return False

    def get_analysis(self, video_id: str, comment_id: str) -> Optional[Dict]:
        """
        Recupera el análisis de un comentario específico.
        
        Returns:
            Dict con los resultados o None si no se encuentra
        """
        query = """
        SELECT * FROM comment_analysis
        WHERE video_id = %s AND comment_id = %s;
        """
        try:
            self.cursor.execute(query, (video_id, comment_id))
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except psycopg2.Error as e:
            print(f"Error recuperando el análisis: {e}")
            return None

    def get_video_statistics(self, video_id: str) -> Optional[Dict]:
        """
        Obtiene estadísticas de hate speech para un video específico.
        
        Returns:
            Dict con estadísticas o None en caso de error
        """
        query = """
        SELECT 
            COUNT(*) as total_comments,
            SUM(CASE WHEN traditional_hate = 1 THEN 1 ELSE 0 END) as traditional_hate_count,
            SUM(CASE WHEN transformer_hate = 1 THEN 1 ELSE 0 END) as transformer_hate_count
        FROM comment_analysis
        WHERE video_id = %s;
        """
        try:
            self.cursor.execute(query, (video_id,))
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except psycopg2.Error as e:
            print(f"Error obteniendo estadísticas: {e}")
            return None