# E-Paper Python Dashboard

Модульный дашборд для e-paper дисплеев Waveshare на Raspberry Pi Zero 2 W под DietPi. Показывает дату/время, погоду, локальные датчики, курсы криптовалют, статистику майнинга и секцию неправильных английских глаголов с пагинацией на экране 3.7" (4 градации серого).

English version: [README.md](README.md)

## Возможности

- **Раскладка задаётся конфигом** — каждая строка и элемент экрана описаны в `dashboard.config.json`, менять дашборд можно без правки кода
- **Все адреса сервисов, API-ключи и параметры модели дисплея — в `.env`**, конфиг ссылается на них как `env.ИМЯ`
- **Источники данных**: OpenWeatherMap, платы WiFi-IoT (текстовый протокол `ключ:значение;`), тикеры KuCoin, статистика пула Solopool, JSONP-дашборд майнера Nano3
- **Кэширование с пометкой устаревания** — если источник недоступен, показывается последнее известное значение (можно светло-серым); отсутствующие данные можно скрыть или заменить фолбэком из другого источника
- **Секция глаголов** — читает `verbs.json`, разбивает на страницы по свободной области экрана и листает страницу каждые 5 минут частичной перерисовкой
- **Тестируется без железа** — рендерер работает без драйвера EPD; `--dry-run` собирает весь дашборд в `saved_display_image.png`

## Железо

- Raspberry Pi Zero 2 W (подойдёт любая Pi)
- Waveshare 3.7" e-Paper HAT (`epd3in7`, 280×480, 4 градации серого) — другие модели настраиваются через `.env`
- Включённый SPI (`dtparam=spi=on` в `config.txt`)

## Установка (DietPi / Raspberry Pi OS)

```bash
apt install -y python3 python3-pil python3-requests python3-spidev python3-gpiozero python3-lgpio
git clone https://github.com/dzmitryNz/epd-e-paper-python-dashboard.git
cd epd-e-paper-python-dashboard

# Драйвер Waveshare не входит в репозиторий — скопируйте его из примеров Waveshare
# (https://github.com/waveshareteam/e-Paper) в lib/:
#   lib/waveshare_epd/epd3in7.py, epdconfig.py, ...

cp .env.example .env
nano .env   # заполнить адреса и ключи
```

### Переменные `.env`

| Переменная | Описание |
|---|---|
| `EPD_MODEL` | Имя модуля драйвера Waveshare из `lib/waveshare_epd` (например `epd3in7`) |
| `EPD_WIDTH`, `EPD_HEIGHT`, `EPD_ROTATION` | Геометрия дисплея |
| `SENSORS_URL_1`, `SENSORS_URL_2` | Платы WiFi-IoT, отдающие `dsw1:12.5;dsw2:7.25;...` |
| `WEATHER_URL`, `OPENWEATHERMAP_API_KEY` | Эндпоинт OpenWeatherMap и API-ключ (город/язык задаются в конфиге) |
| `KUCOIN_URL` | Эндпоинт KuCoin all-tickers (публичный, ключ не нужен) |
| `SOLOPOOL_URL` | URL API аккаунта Solopool (адрес кошелька — часть URL) |
| `NANO3STATS_URL`, `NANO3STATS_AUTH` | Эндпоинт дашборда майнера Nano3 и значение его cookie `auth` |

## Запуск

```bash
python3 epaper_dashboard.py            # отрисовать и вывести на экран
python3 epaper_dashboard.py --dry-run  # только собрать saved_display_image.png
```

Автозапуск при загрузке (`crontab -e` от root):

```
@reboot sleep 30 && cd /путь/к/epd-e-paper-python-dashboard && python3 epaper_dashboard.py >> /var/log/epaper.log 2>&1
```

Для периодического обновления добавьте обычную cron-запись (например, каждые 10 минут).

## Формат конфигурации

`dashboard.config.json` состоит из секций `display`, `fonts`, `layout`, `services` и `dashboard`.

Любое строковое значение в конфиге может быть `env.ИМЯ` или `${ИМЯ}` — при загрузке оно заменяется значением переменной окружения (`.env` загружается первым).

### Строки и элементы дашборда

`dashboard.lines` — упорядоченный список строк экрана. У строки есть необязательные `startY`, `startX`, `afterY` и список `items`:

| Поле элемента | Значение |
|---|---|
| `type` | Ключ данных (`dsw1`, `temp`, `BTC-USDC`, `hashrate`, ...) или специальный: `datetime`, `text`, `sunrise`, `sunset` |
| `category` | Источник: `sensors`, `weather`, `kucoin`, `solopool`, `nano3stats` |
| `text` | Текст статической подписи (для `type: "text"`) |
| `prefix`, `suffix` | Строки до и после значения |
| `font`, `colour` | Имя шрифта из `fonts`; цвет (`GRAY1`..`GRAY4` для 4-градационного режима) |
| `startX`, `offsetY`, `afterX` | Позиционирование: абсолютный X в строке, сдвиг по Y, отступ после |
| `format` | strftime-формат для `datetime`/`sunrise`/`sunset` или `hashrate` для сокращений T/G/M |
| `map` | Подстановка значений, например `{"0": "Lo", "1": "Mi", "2": "Hi"}` |
| `fallback` | Запасной источник при отсутствии значения: `{"type": "temp", "category": "weather"}` |
| `hideIfMissing` | Не выводить ничего вместо `N/A`, если значения нет |

Строка с `"type": "verbs"` занимает остаток экрана таблицей глаголов с пагинацией (поля: `font`, `lineHeight`, `colour`, `secondaryColour`). Страница переключается каждые 5 минут; прогресс хранится в `verbs_state.json`.

Устаревшие (кэшированные) значения рисуются цветом `display.oldDataColour`.

## Разработка

```bash
python3 -m unittest discover -s tests   # тесты (железо не нужно)
python3 epaper_dashboard.py --dry-run   # визуальная проверка: saved_display_image.png
```

Структура проекта:

```
epaper_dashboard.py     # точка входа
config_loader.py        # загрузка .env + подстановка env.ИМЯ + валидация
data_loader.py          # опрос всех источников, слияние с кэшем
data_storage.py         # кэш dashboard_data.json
display_renderer.py     # рендеринг по конфигу, драйвер EPD грузится лениво
verbs.py                # список глаголов, пагинация, состояние
services/               # по модулю на источник данных
tests/                  # тесты unittest
```
