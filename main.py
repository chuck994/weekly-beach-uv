import json
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

# Beach and nearby reference locations.
LOCATIONS = {
"Isle of Palms": {
"latitude": 32.7868,
"longitude": -79.7947,
},
"Sullivan's Island": {
"latitude": 32.7632,
"longitude": -79.8367,
},
"Mount Pleasant": {
"latitude": 32.8323,
"longitude": -79.8284,
},
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

url = (
"https://api.open-meteo.com/v1/forecast?"
+ urllib.parse.urlencode(params)
)

request = urllib.request.Request(
url,
headers={"User-Agent": "WeeklyBeachUVOutlook/1.0"},
)

with urllib.request.urlopen(request, timeout=30) as response:
data = json.loads(response.read().decode("utf-8"))

hourly = data.get("hourly", {})
daily = data.get("daily", {})

times = hourly.get("time", [])
uv_values = hourly.get("uv_index", [])
clouds = hourly.get("cloud_cover", [])
temperatures = hourly.get("temperature_2m", [])
rain_chances = hourly.get("precipitation_probability", [])
weather_codes = hourly.get("weather_code", [])

daily_times = daily.get("time", [])
daily_uv = daily.get("uv_index_max", [])
sunrises = daily.get("sunrise", [])
sunsets = daily.get("sunset", [])

hours = []

for i, timestamp in enumerate(times):
hours.append({
"time": timestamp,
"uv_index": uv_values[i] if i < len(uv_values) else None,
"cloud_cover_percent": (
clouds[i] if i < len(clouds) else None
),
"temperature_f": (
temperatures[i] if i < len(temperatures) else None
),
"precipitation_probability_percent": (
rain_chances[i] if i < len(rain_chances) else None
),
"weather_code": (
weather_codes[i] if i < len(weather_codes) else None
),
})

days = []

for i, date in enumerate(daily_times):
day_hours = [
hour for hour in hours
if hour["time"].startswith(date)
]

valid_uv = [
hour["uv_index"]
for hour in day_hours
if isinstance(hour["uv_index"], (int, float))
]

best_window = None

# Find the lowest-UV two-hour window during daylight.
# This is a comparison of forecast UV, not a guarantee
# that the time is safe from sun exposure.
sunrise = sunrises[i] if i < len(sunrises) else None
sunset = sunsets[i] if i < len(sunsets) else None

daylight_hours = [
hour for hour in day_hours
if sunrise and sunset
and sunrise[11:16] <= hour["time"][11:16] <= sunset[11:16]
and isinstance(hour["uv_index"], (int, float))
]

candidates = []

for j in range(len(daylight_hours) - 1):
pair = daylight_hours[j:j + 2]

first_time = datetime.fromisoformat(pair[0]["time"])
second_time = datetime.fromisoformat(pair[1]["time"])

if (second_time - first_time).total_seconds() == 3600:
candidates.append(pair)

if candidates:
best_pair = min(
candidates,
key=lambda pair: sum(
hour["uv_index"] for hour in pair
) / len(pair),
)
best_window = {
"start": best_pair[0]["time"],
"end": best_pair[1]["time"],
"average_uv_index": round(
sum(hour["uv_index"] for hour in best_pair) / 2,
1,
),
"note": "Lowest-UV two-hour window found in the forecast",
}

days.append({
"date": date,
"uv_index_max": (
daily_uv[i] if i < len(daily_uv) else None
),
"sunrise": sunrise,
"sunset": sunset,
"hours_with_data": len(valid_uv),
"best_lower_uv_window": best_window,
"hourly": day_hours,
})

return {
"name": name,
"latitude": coordinates["latitude"],
"longitude": coordinates["longitude"],
"timezone": data.get("timezone", TIMEZONE),
"forecast_days": days,
}


def main():
generated_at = datetime.now(ZoneInfo(TIMEZONE)).isoformat()

result = {
"generated_at": generated_at,
"timezone": TIMEZONE,
"data_source": "Open-Meteo Forecast API",
"source_url": "https://open-meteo.com/",
"disclaimer": (
"Forecasts can change. Missing values are not estimates. "
"Cloud cover does not eliminate UV exposure. "
"Use sun protection when the UV Index is 3 or higher."
),
"locations": {},
"errors": [],
}

for name, coordinates in LOCATIONS.items():
try:
print(f"Fetching forecast for {name}...")
result["locations"][name] = fetch_forecast(
name, coordinates
)
print(f"Forecast received for {name}.")
except Exception as error:
message = f"{name}: {type(error).__name__}: {error}"
result["errors"].append(message)
print(f"WARNING: Could not fetch {message}")

if not result["locations"]:
raise RuntimeError(
"No forecasts were retrieved. Check the API connection "
"and try running the workflow again."
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
json.dump(result, file, indent=2, ensure_ascii=False)

print(f"Saved forecast data to {OUTPUT_FILE}.")


if __name__ == "__main__":
main()
