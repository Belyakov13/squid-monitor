#!/bin/bash
echo "Установка Redis..."
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
echo "Redis установлен и запущен!"
