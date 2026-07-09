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

# Порт для Back4app
EXPOSE 8080

RUN python manage.py collectstatic --noinput

# Зверни увагу: тут ми замінили invest.wsgi на invest_project.wsgi
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "invest_project.wsgi:application"]
