# E-Paper Python Dashboard

Модульны дашборд для e-paper дысплеяў Waveshare на Raspberry Pi Zero 2 W пад DietPi. Паказвае дату/час, надвор'е, лакальныя датчыкі, курсы криптавалют, статыстыку майнінгу і секцыю няправільных англійскіх дзеясловаў з пагінацыяй на экране 3.7" (4 градацыі шэрага).

English version: [README.md](README.md)

## Магчымасці

- **Раскладка задаецца канфігам** — кожны радок і элемент экрана апісаны ў `dashboard.config.json`, змяняць дашборд можна без праўкі кода
- **Усе адрасы сэрвісаў, API-ключы і параметры мадэлі дысплея — у `.env`**, канфіг спасылаецца на іх як `env.ІМЯ`
- **Крыніцы даных**: OpenWeatherMap, платы WiFi-IoT (тэкставы пратакол `ключ:значэнне;`), тыкеры KuCoin, статыстыка пула Solopool, JSONP-дашборд майнера Nano3, Home Assistant REST API (статус гаражнай аўтаматыкі)
- **Кэшаванне з пазнакай устарэлых даных** — калі крыніца недаступная, паказваецца апошняе вядомае значэнне (можна светла-шэрым); адсутныя даныя можна схаваць або замяніць фолбэкам з іншай крыніцы
- **Секцыя дзеясловаў** — чытае `verbs.json`, разбівае на старонкі па вольнай вобласці экрана і гартае старонку кожныя 5 хвілін частковай перамалёўкай
- **Тэстуецца без жалеза** — рэндэрар працуе без драйвера EPD; `--dry-run` збірае ўвесь дашборд у `saved_display_image.png`

## Жалеза

- Raspberry Pi Zero 2 W (падыдзе любая Pi)
- Waveshare 3.7" e-Paper HAT (`epd3in7`, 280×480, 4 градацыі шэрага) — іншыя мадэлі наладжваюцца праз `.env`
- Уключаны SPI (`dtparam=spi=on` у `config.txt`)

## Усталёўка (DietPi / Raspberry Pi OS)

```bash
apt install -y python3 python3-pil python3-requests python3-spidev python3-gpiozero python3-lgpio
git clone https://github.com/dzmitryNz/epd-e-paper-python-dashboard.git
cd epd-e-paper-python-dashboard

# Драйвер Waveshare не ўваходзіць у рэпазіторый — скапіруйце яго з прыкладаў Waveshare
# (https://github.com/waveshareteam/e-Paper) у lib/:
#   lib/waveshare_epd/epd3in7.py, epdconfig.py, ...

cp .env.example .env
nano .env   # запоўніць адрасы і ключы
```

Для беларускай даты на экране згенеруйце лакаль:

```bash
echo 'be_BY.UTF-8 UTF-8' >> /etc/locale.gen
locale-gen
```

### Доступ да Home Assistant

Гаражная аўтаматыка (асобны праект `garageManager`) знаходзіцца не ў той жа
сетцы — яе OrangePi перадае MQTT праз Tailscale у Home Assistant на хатнім
серверы. Два варыянты для гэтай платы:

- **Плата ў той жа хатняй лакальнай сетцы, што і хост Home Assistant**
  (звычайны выпадак): проста ўкажыце `HA_URL` як LAN IP хатняга сервера,
  напрыклад `http://192.168.1.X:8123`. Tailscale на плаце не патрэбны.
  
- **Home Assistant даступны толькі праз Tailscale** з сеткі гэтай платы:
  усталюйце Tailscale і на плату (`curl -fsSL
  https://tailscale.com/install.sh | sh && tailscale up`), потым выкарыстайце
  Tailscale hostname/IP (`100.x.x.x`) як `HA_URL`.

У любым выпадку згенеруйце доўгачасовы токен доступу на старонцы профілю
Home Assistant (укладка Security → "Long-lived access tokens" → Create
Token) і пакладзіце яго ў `HA_TOKEN`. Мапа `services.homeassistant.entities`
у `dashboard.config.json` пералічвае, якія entity_id забіраць — падладзьце
яе пад рэальныя entity_id вашай Home Assistant.

### Пераменныя `.env`

| Пераменная | Апісанне |
|---|---|
| `EPD_MODEL` | Імя модуля драйвера Waveshare з `lib/waveshare_epd` (напрыклад `epd3in7`) |
| `EPD_WIDTH`, `EPD_HEIGHT`, `EPD_ROTATION` | Геаметрыя дысплея |
| `SENSORS_URL_1`, `SENSORS_URL_2` | Платы WiFi-IoT, якія аддаюць `dsw1:12.5;dsw2:7.25;...` |
| `WEATHER_URL`, `OPENWEATHERMAP_API_KEY` | Эндпоінт OpenWeatherMap і API-ключ (горад/мова задаюцца ў канфігу) |
| `KUCOIN_URL` | Эндпоінт KuCoin all-tickers (публічны, ключ не патрэбны) |
| `SOLOPOOL_URL` | URL API акаўнта Solopool (адрас кашалька — частка URL) |
| `NANO3STATS_URL`, `NANO3STATS_AUTH` | Эндпоінт дашборда майнера Nano3 і значэнне яго cookie `auth` |
| `HA_URL`, `HA_TOKEN` | Базавы URL Home Assistant (без канчатковага слэша і без `/api`) і доўгачасовы токен доступу |

## Запуск

```bash
python3 epaper_dashboard.py            # адмаляваць і вывесці на экран
python3 epaper_dashboard.py --dry-run  # толькі сабраць saved_display_image.png
```

Аўтазапуск пры загрузцы (`crontab -e` ад root):

```
@reboot sleep 30 && cd /шлях/да/epd-e-paper-python-dashboard && python3 epaper_dashboard.py >> /var/log/epaper.log 2>&1
*/10 * * * * cd /шлях/да/epd-e-paper-python-dashboard && python3 epaper_dashboard.py >> /var/log/epaper.log 2>&1
```

Першы радок малюе дашборд адзін раз пасля загрузкі, другі абнаўляе яго кожныя 10 хвілін (скрыпт аднаразовы: адмалёўвае, абнаўляе экран і завяршаецца). На DietPi `/var/log` жыве ў RAM, таму лог не зношвае SD-карту.

## Фармат канфігурацыі

`dashboard.config.json` складаецца з секцый `display`, `fonts`, `layout`, `services` і `dashboard`.

Любое радковае значэнне ў канфігу можа быць `env.ІМЯ` або `${ІМЯ}` — пры загрузцы яно замяняецца значэннем пераменнай асяроддзя (`.env` загружаецца першым).

### Радкі і элементы дашборда

`dashboard.lines` — упарадкаваны спіс радкоў экрана. У радка ёсць неабавязковыя `startY`, `startX`, `afterY` і спіс `items`:

| Поле элемента | Значэнне |
|---|---|
| `type` | Ключ даных (`dsw1`, `temp`, `BTC-USDC`, `hashrate`, ...) або спецыяльны: `datetime`, `text`, `sunrise`, `sunset` |
| `category` | Крыніца: `sensors`, `weather`, `kucoin`, `solopool`, `nano3stats` |
| `text` | Тэкст статычнага подпісу (для `type: "text"`) |
| `prefix`, `suffix` | Радкі да і пасля значэння |
| `font`, `colour` | Імя шрыфта з `fonts`; колер (`GRAY1`..`GRAY4` для 4-градацыйнага рэжыму) |
| `startX`, `offsetY`, `afterX` | Пазіцыянаванне: абсалютны X у радку, зрух па Y, водступ пасля |
| `format` | strftime-фармат для `datetime`/`sunrise`/`sunset` або `hashrate` для скарачэнняў T/G/M |
| `map` | Падстаноўка значэнняў, напрыклад `{"0": "Lo", "1": "Mi", "2": "Hi"}` |
| `fallback` | Запасная крыніца пры адсутнасці значэння: `{"type": "temp", "category": "weather"}` |
| `hideIfMissing` | Не выводзіць нічога замест `N/A`, калі значэння няма |

Радок з `"type": "verbs"` займае рэшту экрана табліцай дзеясловаў з пагінацыяй (палі: `font`, `lineHeight`, `colour`, `secondaryColour`, а таксама неабавязковы `maxHeight`, каб абмежаваць вышыню блока замест таго, каб займаць увесь астатні экран — карысна, калі пасля яго ідуць яшчэ радкі). Старонка пераключаецца кожныя 5 хвілін; прагрэс захоўваецца ў `verbs_state.json`.

Устарэлыя (кэшаваныя) значэнні малююцца колерам `display.oldDataColour`.

## Распрацоўка

```bash
python3 -m unittest discover -s tests   # тэсты (жалеза не патрэбна)
python3 epaper_dashboard.py --dry-run   # візуальная праверка: saved_display_image.png
```

Структура праекта:

```
epaper_dashboard.py     # кропка ўваходу
config_loader.py        # загрузка .env + падстаноўка env.ІМЯ + валідацыя
data_loader.py          # апытанне ўсіх крыніц, зліццё з кэшам
data_storage.py         # кэш dashboard_data.json
display_renderer.py     # рэндэрынг па канфігу, драйвер EPD грузіцца лена
verbs.py                # спіс дзеясловаў, пагінацыя, стан
services/               # па модулі на крыніцу даных
tests/                  # тэсты unittest
```
