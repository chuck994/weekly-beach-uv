
import json
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

LOCATIONS = {
    "Isle of Palms": {"latitude": 32.7868, "longitude": -79.7947},
    "Sullivan's Island": {"latitude": 32.7632, "longitude": -79.8367},
    "Mount Pleasant": {"latitude": 32.8323, "longitude": -79.8284},
}

TIMEZONE = "America/New_York"
OUTPUT_FILE = "forecast.json"


def fetch_forecast(name, coordinates):
    """Download one location's hourly UV and weather forecast."""
    params = {
        "latitude": coordinates["latitude"],
        "longitude": coordinates["longitude"],
        "hourly": (
            "uv_index,cloud_cover,temperature_2m,"
            "precipitation_probability,weather_code"
        ),
        "daily": "uv_index_max,sunrise,sunset",
        "temperature_unit": "fahrenheit",
        "timezone": TIMEZONE,
        "forecast_days": 7,
    }

    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "WeeklyBeachUVOutlook/1.0"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)

    data["location_name"] = name
    data["coordinates"] = coordinates
    return data


def main():
    generated_at = datetime.now(ZoneInfo(TIMEZONE)).isoformat()

    forecast = {
        "generated_at": generated_at,
        "timezone": TIMEZONE,
        "source": "Open-Meteo Forecast API",
        "source_url": "https://open-meteo.com/",
        "locations": {},
    }

    for name, coordinates in LOCATIONS.items():
        print(f"Fetching forecast for {name}...")
        forecast["locations"][name] = fetch_forecast(name, coordinates)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(forecast, file, indent=2)

    print(f"Saved forecast data to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
