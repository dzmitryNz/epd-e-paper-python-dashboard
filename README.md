# E-Paper Python Dashboard

A modular dashboard for Waveshare e-paper displays, built for a Raspberry Pi Zero 2 W running DietPi. Renders date/time, weather, local WiFi-IoT sensors, crypto prices, mining stats, and a paginated English irregular verbs study section on a 3.7" 4-gray e-paper screen.

Беларуская версія: [README.be.md](README.be.md)

## Features

- **Config-driven layout** — every line and item on the screen is described in `dashboard.config.json`, no code changes needed to rearrange the dashboard
- **All service addresses, API keys, and display model parameters live in `.env`** — the config references them as `env.NAME`
- **Data sources**: OpenWeatherMap, WiFi-IoT sensor boards (plain-text `key:value;` protocol), KuCoin tickers, Solopool mining stats, Nano3 miner JSONP dashboard, Home Assistant REST API (garage automation status)
- **Caching with staleness marking** — when a source is offline the last known value is shown (optionally in a lighter gray), fully missing data can be hidden or replaced with a fallback source
- **Verbs section** — reads `verbs.json`, paginates it into the free screen area, and flips the page every 5 minutes with a partial redraw
- **Testable without hardware** — the renderer works without the EPD driver; `--dry-run` renders the full dashboard into `saved_display_image.png`

## Hardware

- Raspberry Pi Zero 2 W (any Pi should work)
- Waveshare 3.7" e-Paper HAT (`epd3in7`, 280×480, 4 gray levels) — other models can be configured via `.env`
- SPI enabled (`dtparam=spi=on` in `config.txt`)

## Installation (DietPi / Raspberry Pi OS)

```bash
apt install -y python3 python3-pil python3-requests python3-spidev python3-gpiozero python3-lgpio
git clone https://github.com/dzmitryNz/epd-e-paper-python-dashboard.git
cd epd-e-paper-python-dashboard

# Waveshare driver is not bundled — copy it from the Waveshare examples
# (https://github.com/waveshareteam/e-Paper) into lib/:
#   lib/waveshare_epd/epd3in7.py, epdconfig.py, ...

cp .env.example .env
nano .env   # fill in addresses and keys
```

### Reaching Home Assistant

The garage automation system (separate `garageManager` project) is not on the
same network as the garage — its OrangePi bridges MQTT out via Tailscale to a
Home Assistant instance on the home server. Two cases for this board:

- **This board is on the same home LAN as the Home Assistant host** (the
  common case, since the home server and this board are both at home): just
  point `HA_URL` at the home server's LAN IP, e.g. `http://192.168.1.X:8123`.
  No Tailscale needed on this board.
- **Home Assistant is only reachable over Tailscale** from this board's
  network: install Tailscale on this board too (`curl -fsSL
  https://tailscale.com/install.sh | sh && tailscale up`), then use the
  Tailscale hostname/IP (`100.x.x.x`) as `HA_URL`.

Either way, generate a long-lived access token from the Home Assistant user
profile page (Security tab → "Long-lived access tokens" → Create Token) and
put it in `HA_TOKEN`. The `services.homeassistant.entities` map in
`dashboard.config.json` lists which entity_ids to fetch — adjust it to match
the actual entity_ids registered in your Home Assistant instance.

### `.env` variables

| Variable | Description |
|---|---|
| `EPD_MODEL` | Waveshare driver module name from `lib/waveshare_epd` (e.g. `epd3in7`) |
| `EPD_WIDTH`, `EPD_HEIGHT`, `EPD_ROTATION` | Display geometry |
| `SENSORS_URL_1`, `SENSORS_URL_2` | WiFi-IoT sensor boards returning `dsw1:12.5;dsw2:7.25;...` |
| `WEATHER_URL`, `OPENWEATHERMAP_API_KEY` | OpenWeatherMap endpoint and API key (city/lang are set in the config) |
| `KUCOIN_URL` | KuCoin all-tickers endpoint (public, no key needed) |
| `SOLOPOOL_URL` | Solopool account API URL (wallet address is part of the URL) |
| `NANO3STATS_URL`, `NANO3STATS_AUTH` | Nano3 miner dashboard endpoint and its `auth` cookie value |
| `HA_URL`, `HA_TOKEN` | Home Assistant base URL (no trailing slash, no `/api`) and a long-lived access token (Home Assistant profile → Security → Long-lived access tokens) |

## Running

```bash
python3 epaper_dashboard.py            # render + push to the display
python3 epaper_dashboard.py --dry-run  # render to saved_display_image.png only
```

Autostart on boot (`crontab -e` as root):

```
@reboot sleep 30 && cd /path/to/epd-e-paper-python-dashboard && python3 epaper_dashboard.py >> /var/log/epaper.log 2>&1
*/10 * * * * cd /path/to/epd-e-paper-python-dashboard && python3 epaper_dashboard.py >> /var/log/epaper.log 2>&1
```

The first line draws the dashboard once after boot, the second refreshes it every 10 minutes (the script is one-shot: it renders, updates the display, and exits). On DietPi `/var/log` lives in RAM, so the log does not wear the SD card.

## Configuration format

`dashboard.config.json` has four sections: `display`, `fonts`, `layout`, `services`, and `dashboard`.

Any string value anywhere in the config may be `env.NAME` or `${NAME}` — it is replaced with the environment variable at load time (`.env` is loaded first).

### Dashboard lines and items

`dashboard.lines` is an ordered list of screen lines. Each line has optional `startY`, `startX`, `afterY` and a list of `items`:

| Item field | Meaning |
|---|---|
| `type` | Data key (`dsw1`, `temp`, `BTC-USDC`, `hashrate`, ...) or special: `datetime`, `text`, `sunrise`, `sunset` |
| `category` | Data source: `sensors`, `weather`, `kucoin`, `solopool`, `nano3stats` |
| `text` | Static label text (for `type: "text"`) |
| `prefix`, `suffix` | Strings around the value |
| `font`, `colour` | Font name from `fonts`; colour (`GRAY1`..`GRAY4` for 4-gray mode) |
| `startX`, `offsetY`, `afterX` | Positioning: absolute X within the line, Y nudge, spacing after |
| `format` | `datetime`/`sunrise`/`sunset` strftime format, or `hashrate` for T/G/M shorthand |
| `map` | Value substitution map, e.g. `{"0": "Lo", "1": "Mi", "2": "Hi"}` |
| `fallback` | Alternative source when the value is missing: `{"type": "temp", "category": "weather"}` |
| `hideIfMissing` | Render nothing instead of `N/A` when the value is missing |

A line with `"type": "verbs"` fills the rest of the screen with the paginated verbs table (fields: `font`, `lineHeight`, `colour`, `secondaryColour`, and optional `maxHeight` to cap the block's height instead of filling the rest of the screen — useful when lines follow it). The page advances every 5 minutes; progress is persisted in `verbs_state.json`.

Stale (cached) values are drawn in `display.oldDataColour`.

## Development

```bash
python3 -m unittest discover -s tests   # run the test suite (no hardware needed)
python3 epaper_dashboard.py --dry-run   # visual check: inspect saved_display_image.png
```

Project structure:

```
epaper_dashboard.py     # entry point
config_loader.py        # .env loading + env.NAME substitution + validation
data_loader.py          # orchestrates all sources, merges with cache
data_storage.py         # dashboard_data.json cache
display_renderer.py     # config-driven rendering, EPD driver loaded lazily
verbs.py                # verbs list, pagination, state
services/               # one module per data source
tests/                  # unittest suite
```
