#!/bin/bash

# Активация виртуального окружения
#source /home/rbstr/epaper/bin/activate

# Переход в директорию скрипта
cd /home/rbstr/scripts

# Запуск скрипта с обработкой ошибок
python3 sensors6-3.py "$@" 2>&1

# Деактивация окружения
#deactivate
