# Use a imagem base oficial do Python
FROM python:3.11-slim

# Instalar dependências do sistema (incluindo FFmpeg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho
WORKDIR /app

# Copiar o ficheiro de requisitos e instalar as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação
COPY . .

# Expor a porta que o Uvicorn irá usar
EXPOSE 8000

# Comando para iniciar a aplicação
# Nota: A aplicação deve ser iniciada com o uvicorn, referenciando o módulo principal (main:app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
