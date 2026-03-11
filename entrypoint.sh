#!/bin/sh

# Salir inmediatamente si un comando falla
set -e

echo "--- Aplicando migraciones ---"
python manage.py migrate --noinput

echo "--- Creando superusuario (si no existe) ---"
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin12345')
    print('Superusuario creado exitosamente')
else:
    print('El superusuario ya existe')
"

echo "--- Arrancando Gunicorn ---"
exec gunicorn kanban_project.wsgi:application --bind 0.0.0.0:8000