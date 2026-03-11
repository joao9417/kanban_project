# Usar imagen oficial de Python ligera
FROM python:3.13-slim

# Evitar que Python genere archivos .pyc y permitir que los logs salgan directo a la consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crear y establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . /app/

# Dar permisos de ejecución al script de entrada
RUN chmod +x /app/entrypoint.sh

# Crear carpeta para estáticos y recolectarlos
RUN python manage.py collectstatic --noinput

# Puerto que usará la app (Render o similar lo asignarán automáticamente)
EXPOSE 8000

# Usar el script como comando de inicio en lugar de llamar a gunicorn directo
CMD ["/app/entrypoint.sh"]
