# Usa la imagen base de Python
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de dependencias
COPY ./requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt && pip install uvicorn

# Copia todo el proyecto dentro del contenedor
COPY . .

# Expone el puerto que Streamlit usará
EXPOSE 8501

# Comando para ejecutar la app
CMD ["sh", "-c", "streamlit run run.py --server.port=$PORT"]
