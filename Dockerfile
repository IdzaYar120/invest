# Використовуємо офіційний образ Python
FROM python:3.10-slim

# Встановлюємо змінні оточення для Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Встановлюємо робочу директорію всередині контейнера
WORKDIR /code

# Встановлюємо системні залежності, якщо вони потрібні (наприклад, для PostgreSQL чи подушки)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо requirements і встановлюємо залежності
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код проекту в контейнер
COPY . /code/

# Важливо для Hugging Face: вони вимагають порт 7860
EXPOSE 7860

# Збираємо статичні файли (якщо налаштовано STATIC_ROOT)
RUN python manage.py collectstatic --noinput

# Запуск сервера через Gunicorn (або Daphne, якщо у тебе ASGI/чат)
# Замість "invest.wsgi:application" переконайся, що в тебе саме така назва в invest/wsgi.py
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "invest.wsgi:application"]
