# weather_client.py
"""
Example module that imports fetch_weather_details from weather.py
and uses it inside another Python program.
"""

from weather import fetch_weather_details


def get_weather_and_print(city: str):
    """
    A helper function that retrieves weather information
    and prints it in a formatted manner.
    """
    report = fetch_weather_details(city)

    if "error" in report:
        print("\n❌ Error:", report["error"])
        return

    print(f"\n🌤 Weather Report for {report['city']}:")
    print(f"• Temperature: {report['temperature']}")
    print(f"• Humidity: {report['humidity']}")
    print(f"• Wind Speed: {report['wind_speed']}")
    print(f"• Rain Probability: {report['rain_probability']}")

# main.py

from gps_server import get_gps_location
import json
import os
import requests

# Windows-safe temp file path
file_path = r"C:\Users\admin\AppData\Local\Temp\gps_coords_temp.json"


# ----------------------------
# REVERSE GEOCODING FUNCTION
# ----------------------------
def get_city_from_coords(lat, lon):
    """
    Finds city name from latitude and longitude using OpenStreetMap API.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,
        "addressdetails": 1
    }

    try:
        response = requests.get(url, params=params, headers={"User-Agent": "PythonApp"})
        data = response.json()

        city = (
            data.get("address", {}).get("city")
            or data.get("address", {}).get("town")
            or data.get("address", {}).get("village")
            or data.get("address", {}).get("state")
            or "Unknown"
        )

        return city

    except Exception as e:
        print(f"Error fetching city: {e}")
        return "Unknown"


# ----------------------------
# READ OLD GPS FILE FUNCTION
# ----------------------------
def retrieve_coordinates_from_file(path):
    """
    Attempts to read old GPS coordinates from JSON.
    Returns (lat, lon) OR (None, None) if file missing/invalid.
    """
    if not os.path.exists(path):
        print("⚠ No previous GPS data found. Finding location again...\n")
        return None, None

    try:
        with open(path, "r") as f:
            data = json.load(f)

        lat = data.get("latitude")
        lon = data.get("longitude")

        if lat is None or lon is None:
            print("⚠ Previous GPS file found but data incomplete. Finding location again...\n")
            return None, None

        print("📄 Retrieved previous GPS data:")
        print(f"Latitude: {lat}")
        print(f"Longitude: {lon}")

        return lat, lon

    except:
        print("⚠ Error reading old GPS file. Finding location again...\n")
        return None, None


# ----------------------------
# MAIN EXECUTION
# ----------------------------
if __name__ == "__main__":

    # 1) FIRST TRY READING OLD GPS DATA
    old_lat, old_lon = retrieve_coordinates_from_file(file_path)

    if old_lat is not None and old_lon is not None:
        print("=" * 50)
        print("✅ Reusing previous GPS location:")
        print(f"Latitude: {old_lat}")
        print(f"Longitude: {old_lon}")

        city = get_city_from_coords(old_lat, old_lon)
        print(f"🗺 City: {city}")

        print("=" * 50)

    else:
        # 2) IF NO OLD DATA → GET NEW LOCATION
        print("📡 Getting fresh GPS location...\n")
        new_coords = get_gps_location()

        print("\n" + "=" * 50)
        if new_coords:
            lat, lon = new_coords
            print("✅ New GPS Location:")
            print(f"Latitude: {lat}")
            print(f"Longitude: {lon}")

            city = get_city_from_coords(lat, lon)
            print(f"🗺 City: {city}")

        else:
            print("❌ Failed to retrieve new GPS location.")

        print("=" * 50)

if __name__ == "__main__":
    # Change your test city here
    get_weather_and_print(city)
