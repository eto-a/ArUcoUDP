# ArUco AprilTag UDP Tracker

Детектор AprilTag (36h11) с трансляцией координат по UDP.

## Установка
```bash
pip install -r requirements.txt
```

## Запуск
```bash
python main.py
```

## Сборка EXE
```bash
pyinstaller --onefile --noconsole main.py
```

## UDP Формат
`id;x;y;angle`
- **id**: ID маркера
- **x, y**: Центр в пикселях
- **angle**: Угол 0-360°

## Проверка (UDP)
Для просмотра входящих данных:
```bash
python udp_receiver.py
```

## Структура
- `tracker.py`: Логика детекции и UDP.
- `interface.py`: GUI и потоки.
- `main.py`: Точка входа.
- `udp_receiver.py`: Утилита для теста приема данных.
