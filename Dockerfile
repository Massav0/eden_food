# minimal python 3.11 image
FROM python:3.11-slim

WORKDIR /app

# system deps if needed (imagemagick, etc.)
RUN apt-get update && apt-get install -y build-essential libpq-dev --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# expose port
ENV PORT=8000
EXPOSE 8000

# default command
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8000", "app:app"]
