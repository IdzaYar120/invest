FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

# Змінюємо порт на 8080 (стандарт для Back4app)
EXPOSE 8080

RUN python manage.py collectstatic --noinput

# Змінюємо порт у команді запуску на 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "invest.wsgi:application"]
