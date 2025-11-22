#!/usr/bin/env python3
from __future__ import annotations
import os
import argparse
import typing as t
import requests


BASE_URL = "https://api.openweathermap.org/data/2.5/"
DEFAULT_TIMEOUT = 6 

def _get_api_key(explicit_key: t.Optional[str] = None) -> t.Optional[str]:
    """Return API key from explicit_key or environment variable."""
    if explicit_key:
        return explicit_key
    return os.environ.get("OPENWEATHER_API_KEY")


def _format_value(value: t.Optional[float], fmt: str, fallback: str = "N/A") -> str:
    """Safely format numeric values or return fallback."""
    try:
        if value is None:
            return fallback
        return fmt.format(value)
    except Exception:
        return fallback


def fetch_weather_details(city: str,
                          api_key: t.Optional[str] = None,
                          timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Fetch temperature, humidity, wind speed, and rain probability for a city.

    Returns:
      - On success: dict with keys: city, temperature, humidity, wind_speed, rain_probability
      - On failure: dict with key "error" and an explanatory message.

    Behavior / notes:
      - Uses 'metric' units for both current weather and forecast endpoints.
      - Rain probability is computed as: the maximum 'pop' (probability of precipitation)
        among forecast entries for the next ~24 hours (first 8 forecast items @ 3h interval).
      - Safe against missing fields or partial API failures.
    """
    if not city or not isinstance(city, str):
        return {"error": "Invalid city parameter."}

    key = _get_api_key('dc33ba7d8d00e9fb8038ff70fd673c97')

    city = city.strip()
    print(f"\n--- Looking up weather for {city.upper()} ---")

    current_url = f"{BASE_URL}weather"
    forecast_url = f"{BASE_URL}forecast"

    params_current = {"q": city, "appid": key, "units": "metric"}
    params_forecast = {"q": city, "appid": key, "units": "metric"}

    current_data: t.Optional[dict] = None
    forecast_data: t.Optional[dict] = None

    try:
        resp_curr = requests.get(current_url, params=params_current, timeout=timeout)
        if resp_curr.status_code == 404:
            return {"error": f"City '{city}' not found (404)."}
        resp_curr.raise_for_status()
        current_data = resp_curr.json()
    except requests.exceptions.HTTPError as he:
        # For 401, 403, 4xx, 5xx errors give useful message
        return {"error": f"HTTP error while fetching current weather: {he}"}
    except requests.exceptions.RequestException as re:
        return {"error": f"Network/error while fetching current weather: {re}"}
    except Exception as e:
        return {"error": f"Unexpected error while fetching current weather: {e}"}

    # Forecast is secondary; if it fails we'll still return current data with rain_probability = "N/A"
    try:
        resp_fc = requests.get(forecast_url, params=params_forecast, timeout=timeout)
        resp_fc.raise_for_status()
        forecast_data = resp_fc.json()
    except requests.exceptions.RequestException:
        forecast_data = None

    # --- Extract current data safely ---
    main = current_data.get("main", {}) if isinstance(current_data, dict) else {}
    wind = current_data.get("wind", {}) if isinstance(current_data, dict) else {}

    temp = main.get("temp")
    humidity = main.get("humidity")
    wind_speed = wind.get("speed")

    # --- Compute rain probability ---
    rain_probability = "N/A"
    if forecast_data and isinstance(forecast_data, dict):
        flist = forecast_data.get("list") or []
        # consider up to first 8 entries (~24 hours with 3h forecast intervals)
        if isinstance(flist, list) and len(flist) > 0:
            consider = flist[:8]  # safe slice even if less than 8 entries
            pops = []
            for entry in consider:
                if not isinstance(entry, dict):
                    continue
                # 'pop' might be missing; default to 0
                p = entry.get("pop")
                try:
                    if p is None:
                        p = 0.0
                    # ensure numeric
                    p = float(p)
                    if p < 0:
                        p = 0.0
                    if p > 1:
                        # sometimes API returns percent by mistake — normalize
                        if p > 1 and p <= 100:
                            p = p / 100.0
                        else:
                            p = max(0.0, min(1.0, p))
                    pops.append(p)
                except Exception:
                    # ignore malformed pop values
                    continue
            if pops:
                max_pop = max(pops)
                rain_probability = f"{max_pop * 100:.0f}%"
            else:
                rain_probability = "N/A"

    # Prepare formatted report
    report = {
        "city": city,
        "temperature": _format_value(temp, "{:.1f}°C"),
        "humidity": _format_value(humidity, "{}%", "N/A") if humidity is not None else "N/A",
        "wind_speed": _format_value(wind_speed, "{:.1f} m/s"),
        "rain_probability": rain_probability
    }

    return report


def _print_report(report: dict) -> None:
    """Nicely print the report (handles error messages too)."""
    if report is None:
        print("No data.")
        return
    if "error" in report:
        print("Error:", report["error"])
        return

    print(f"City: {report.get('city')}")
    print(f"Temperature: {report.get('temperature')}")
    print(f"Humidity: {report.get('humidity')}")
    print(f"Wind speed: {report.get('wind_speed')}")
    print(f"Rain probability (next ~24h): {report.get('rain_probability')}")


def _cli_main():
    parser = argparse.ArgumentParser(description="Get current weather + rain probability (OpenWeatherMap).")
    parser.add_argument("--city", "-c", required=True, help="City name (e.g., 'London,UK' or 'Mumbai')")
    parser.add_argument("--api-key", help="OpenWeatherMap API key (optional; overrides env var).")
    args = parser.parse_args()

    report = fetch_weather_details(args.city, api_key=args.api_key)
    _print_report(report)


if __name__ == "__main__":
    _cli_main()
