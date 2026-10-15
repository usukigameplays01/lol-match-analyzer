FROM python:3.12-slim

WORKDIR /app

# Primero las dependencias: así Docker reutiliza esta capa si solo cambia el código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# El código que necesita la API (incluye la página del dashboard)
COPY database.py api.py dashboard.html ./

EXPOSE 8000

# 0.0.0.0 para que la API sea accesible desde fuera del contenedor
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
