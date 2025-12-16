# Dockerfile для Web Interface (Streamlit)
FROM python:3.11-slim
WORKDIR /app
# Установка зависимостей системы и обновление pip
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip setuptools wheel

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей с повторными попытками
RUN pip install --no-cache-dir --retries 5 -r requirements.txt || \
    pip install --no-cache-dir --retries 5 -r requirements.txt

# Копирование кода приложения
COPY . .
# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV WORKER_API_URL=http://worker:8000

# Конфигурация Streamlit
RUN mkdir -p ~/.streamlit && \
    echo "[server]\n" \
    "headless = true\n" \
    "port = 8501\n" \
    "enableCORS = false\n" \
    > ~/.streamlit/config.toml

# Проверка здоровья
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1 || true

# Запуск приложения
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
