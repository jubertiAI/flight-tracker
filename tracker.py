"""
Flight Price Tracker Bot
Checks MUC→MAD direct flight prices via SerpApi and sends Telegram alerts.
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# --- Configuration ---

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

DEPARTURE = "MUC"
ARRIVAL = "MAD"
DATE = "2026-05-15"
PRICE_ALERT_THRESHOLD = 200  # EUR

GOOGLE_FLIGHTS_LINK = (
    "https://www.google.com/travel/flights"
    "?q=flights+from+MUC+to+MAD+on+2026-05-15&type=one-way&stops=nonstop"
)

CSV_PATH = Path(__file__).parent / "price_history.csv"
CSV_COLUMNS = ["date_checked", "airline", "flight_number", "departure", "arrival", "price_eur"]


def check_env_vars():
    """Exit with a clear message if any required env var is missing."""
    missing = []
    if not SERPAPI_KEY:
        missing.append("SERPAPI_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        print(f"Error: missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Set them before running: export SERPAPI_KEY=... etc.", file=sys.stderr)
        sys.exit(1)


def fetch_flights():
    """Call SerpApi Google Flights and return the JSON response."""
    params = {
        "engine": "google_flights",
        "departure_id": DEPARTURE,
        "arrival_id": ARRIVAL,
        "outbound_date": DATE,
        "type": "2",       # one-way
        "stops": "1",      # nonstop only
        "currency": "EUR",
        "hl": "en",
        "gl": "de",
        "api_key": SERPAPI_KEY,
    }
    resp = requests.get("https://serpapi.com/search", params=params, timeout=30)

    if resp.status_code == 429:
        raise RuntimeError("SerpApi rate limit hit (HTTP 429). Will retry next run.")

    resp.raise_for_status()
    return resp.json()


def is_evening_arrival(arrival_time_str):
    """
    Return True if arrival is between 20:00 and 02:00 (next day).
    arrival_time_str looks like "2026-05-15 22:30" or similar from the API.
    We only care about the hour:minute part.
    """
    try:
        # The API returns times in various formats; extract the time portion
        time_part = arrival_time_str.strip().split(" ")[-1]  # "22:30"
        hour = int(time_part.split(":")[0])
        return hour >= 20 or hour < 2
    except (ValueError, IndexError):
        return False


def parse_flights(data):
    """
    Extract flight info from SerpApi response.
    Combines best_flights and other_flights, filters to evening arrivals.
    Returns a list of dicts with: airline, flight_number, departure, arrival, price.
    """
    results = []
    all_flights = data.get("best_flights", []) + data.get("other_flights", [])

    for option in all_flights:
        # Each option has a list of "flights" (legs) and a "price"
        legs = option.get("flights", [])
        price = option.get("price")

        if not legs or price is None:
            continue

        # For nonstop, there should be exactly one leg
        if len(legs) != 1:
            continue

        leg = legs[0]
        departure_time = leg.get("departure_airport", {}).get("time", "")
        arrival_time = leg.get("arrival_airport", {}).get("time", "")
        airline = leg.get("airline", "Unknown")
        flight_number = leg.get("flight_number", "N/A")

        if not is_evening_arrival(arrival_time):
            continue

        results.append({
            "airline": airline,
            "flight_number": flight_number,
            "departure": departure_time,
            "arrival": arrival_time,
            "price": price,
        })

    # Sort cheapest first
    results.sort(key=lambda f: f["price"])
    return results


def log_to_csv(flights):
    """Append flight data to the CSV history file. Creates headers if new."""
    file_exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for flight in flights:
            writer.writerow({
                "date_checked": now,
                "airline": flight["airline"],
                "flight_number": flight["flight_number"],
                "departure": flight["departure"],
                "arrival": flight["arrival"],
                "price_eur": flight["price"],
            })


def send_telegram(message):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Warning: failed to send Telegram message: {e}", file=sys.stderr)


def build_alert_message(flights):
    """Build the Telegram message based on flight results."""
    cheap = [f for f in flights if f["price"] < PRICE_ALERT_THRESHOLD]

    if cheap:
        lines = ["🚨 <b>CHEAP FLIGHT ALERT!</b> 🚨\n"]
        for f in cheap:
            lines.append(
                f"✈️ {f['airline']} {f['flight_number']}\n"
                f"🕐 Departs: {f['departure']} → Arrives: {f['arrival']}\n"
                f"💰 <b>PRICE: {f['price']} EUR</b>\n"
            )
        lines.append(f"🔗 <a href=\"{GOOGLE_FLIGHTS_LINK}\">Book now on Google Flights</a>")
        return "\n".join(lines)

    # No cheap flights — report the cheapest option
    best = flights[0]  # already sorted cheapest-first
    return (
        f"No deals yet. Cheapest direct MUC→MAD May 15: "
        f"<b>{best['price']} EUR</b> with {best['airline']} at {best['departure']}. "
        f"Tracking continues."
    )


def main():
    check_env_vars()
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Checking MUC→MAD flights for {DATE}...")

    try:
        data = fetch_flights()
    except requests.RequestException as e:
        msg = f"API check failed: {e}. Will retry next run."
        print(msg, file=sys.stderr)
        send_telegram(f"⚠️ Flight tracker: {msg}")
        sys.exit(0)
    except RuntimeError as e:
        # Rate limit
        print(str(e), file=sys.stderr)
        sys.exit(0)

    flights = parse_flights(data)

    if not flights:
        msg = "No direct evening flights found for MUC→MAD on May 15."
        print(msg)
        send_telegram(f"✈️ {msg}")
        sys.exit(0)

    log_to_csv(flights)
    print(f"Found {len(flights)} evening flight(s). Logged to {CSV_PATH.name}.")

    message = build_alert_message(flights)
    send_telegram(message)
    print("Telegram alert sent.")


if __name__ == "__main__":
    main()
