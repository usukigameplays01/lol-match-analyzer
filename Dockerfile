FROM python:3.12-slim

WORKDIR /app

# Primero las dependencias: así Docker reutiliza esta capa si solo cambia el código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo el código que necesita la API
COPY database.py api.py ./

EXPOSE 8000

# 0.0.0.0 para que la API sea accesible desde fuera del contenedor
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
