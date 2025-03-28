#!/bin/bash
echo "Запуск сервера с Gunicorn..."
gunicorn squid_monitor.wsgi:application --workers 4 --threads 2 --bind 0.0.0.0:8000 --daemon
echo "Сервер запущен на http://localhost:8000"
