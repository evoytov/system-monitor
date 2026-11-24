# Widget Hardware Stats — Виджет мониторинга системы

## 🎯 Цель
Прозрачный оверлей-виджет для Windows, отображающий реальные метрики GPU, CPU и RAM.

## 🛠 Стек
- Python 3.x
- PyQt6 (интерфейс)
- psutil (CPU/RAM данные)
- pynvml (NVIDIA GPU мониторинг)

## 📦 Установка зависимостей
```bash
pip install PyQt6 psutil nvidia-ml-py
```

## 🚀 Запуск
```bash
python main.py
```

## 📁 Структура проекта
```
WidgetHardwareStats/
├── main.py              # Точка входа
├── collector.py         # Сбор данных о железе
├── widget.py            # PyQt6 виджет UI
├── config.yaml          # Настройки (цвета, шрифты)
└── requirements.txt     # Зависимости
```

## 🎨 Настройка прозрачности
Виджет использует `Qt.WindowTransparentForInput` и имеет полностью прозрачный фон с элементами только в виде текстa и элементов управления.

## ⚙️ Горячие клавиши (опционально)
- `Ctrl+Alt+H` — сворачивание/разворачивание виджета

---
*Создано Hermes Agent для моушен-дизайна*
