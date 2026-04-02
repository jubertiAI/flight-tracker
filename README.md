# Flight Price Tracker Bot

Monitors direct MUC→MAD flight prices for May 15, 2026 and sends Telegram alerts. Checks 6 times a day and logs every result to a CSV file.

## What it does

- **Fetches** nonstop flight prices from SerpApi (Google Flights data)
- **Filters** to evening arrivals only (landing 20:00–02:00)
- **Alerts** via Telegram — loud alert if a flight is under 200 EUR, quiet update otherwise
- **Logs** every price check to `price_history.csv` so you can track trends

## Setup

### 1. Install dependencies

```bash
make install
```

### 2. Set environment variables

You need three keys. Export them in your shell or add to your `.zshrc`/`.bashrc`:

```bash
export SERPAPI_KEY="your-serpapi-api-key"
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export TELEGRAM_CHAT_ID="your-telegram-chat-id"
```

- **SERPAPI_KEY**: Sign up at [serpapi.com](https://serpapi.com/) to get an API key.
- **TELEGRAM_BOT_TOKEN**: Create a bot via [@BotFather](https://t.me/BotFather) on Telegram.
- **TELEGRAM_CHAT_ID**: Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat ID.

### 3. Run a test check

```bash
make check
```

You should receive a Telegram message and see `price_history.csv` created.

## Commands

| Command            | What it does                                         |
|--------------------|------------------------------------------------------|
| `make check`       | Run a single price check right now                   |
| `make schedule`    | Install a cron job for 6 checks/day (Buenos Aires)   |
| `make unschedule`  | Remove the cron job                                  |
| `make history`     | Display the price history CSV in a readable table    |
| `make install`     | Install Python dependencies                          |

## Cron schedule

Runs at these Buenos Aires times (UTC-3): 8am, 11am, 1pm, 4pm, 7pm, 10pm.

Cron output is logged to `cron.log` in the project directory.

## Files

| File               | Purpose                                              |
|--------------------|------------------------------------------------------|
| `tracker.py`       | Main script — fetch, filter, log, alert              |
| `price_history.csv`| Auto-created log of every price check                |
| `requirements.txt` | Python dependencies (just `requests`)                |
| `Makefile`         | Convenience commands                                 |
| `.gitignore`       | Keeps CSV, cache, and secrets out of git             |
