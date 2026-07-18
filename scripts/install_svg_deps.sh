#!/bin/bash
# Скрипт установки зависимостей для svg_converter модуля

echo "Установка зависимостей для svg_converter..."

# Проверка доступности apt
if command -v apt &> /dev/null; then
    echo "Используется apt для установки..."
    
    # Обновление списка пакетов
    sudo apt update
    
    # Попытка установить python3-cairosvg
    echo "Попытка установить python3-cairosvg..."
    if sudo apt install -y python3-cairosvg 2>/dev/null; then
        echo "✓ python3-cairosvg установлен успешно"
        exit 0
    fi
    
    # Если не получилось, пробуем альтернативу
    echo "Попытка установить python3-svglib и python3-reportlab..."
    if sudo apt install -y python3-svglib python3-reportlab 2>/dev/null; then
        echo "✓ python3-svglib и python3-reportlab установлены успешно"
        exit 0
    fi
    
    echo "Не удалось установить через apt. Пробуем pip --user..."
fi

# Если apt не сработал, используем pip --user
if command -v pip3 &> /dev/null; then
    echo "Используется pip3 --user для установки..."
    
    # Попытка установить cairosvg
    echo "Попытка установить cairosvg..."
    if pip3 install --user cairosvg 2>/dev/null; then
        echo "✓ cairosvg установлен успешно"
        exit 0
    fi
    
    # Альтернатива
    echo "Попытка установить svglib и reportlab..."
    if pip3 install --user svglib reportlab 2>/dev/null; then
        echo "✓ svglib и reportlab установлены успешно"
        exit 0
    fi
fi

echo "ОШИБКА: Не удалось установить зависимости автоматически."
echo ""
echo "Попробуйте вручную один из вариантов:"
echo "  1. sudo apt install python3-cairosvg"
echo "  2. sudo apt install python3-svglib python3-reportlab"
echo "  3. pip3 install --user cairosvg"
echo "  4. pip3 install --user svglib reportlab"
echo ""
echo "Для cairosvg может потребоваться: sudo apt install libcairo2-dev"
exit 1

