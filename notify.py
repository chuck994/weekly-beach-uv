
import json
import os
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/New_York")
DASHBOARD_URL = "https://chuck994.github.io/weekly-beach-uv/"
FORECAST_FILE = "forecast.json"

UV_MINIMUM = 6
CLOUD_MAXIMUM = 50
RAIN_MAXIMUM = 30
LOOKAHEAD_DAYS = 3


def main():
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        raise RuntimeError("The NTFY_TOPIC secret is missing.")

    with open(FORECAST_FILE, encoding="utf-8") as file:
        forecast = json.load(file)

    now = datetime.now(TIMEZONE)
    cutoff = now + timedelta(days=LOOKAHEAD_DAYS)
    matches = []

    for location_name, data in forecast["locations"].items():
        hourly = data["hourly"]
        times = hourly["time"]
        uv_values = hourly["uv_index"]
        clouds = hourly["cloud_cover"]
        rain = hourly["precipitation_probability"]
        temps = hourly["temperature_2m"]

        for i, time_text in enumerate(times):
            hour = datetime.fromisoformat(time_text).replace(
                tzinfo=TIMEZONE
            )

            if not (now <= hour <= cutoff):
                continue
            if not (8 <= hour.hour <= 17):
                continue

            uv = uv_values[i]
            cloud = clouds[i]
            rain_chance = rain[i]
            temperature = temps[i]

            if (
                uv is not None
                and cloud is not None
                and rain_chance is not None
                and uv >= UV_MINIMUM
                and cloud <= CLOUD_MAXIMUM
                and rain_chance <= RAIN_MAXIMUM
            ):
                matches.append({
                    "location": location_name,
                    "time": hour,
                    "uv": uv,
                    "cloud": cloud,
                    "rain": rain_chance,
                    "temperature": temperature,
                })

    if not matches:
        print("No qualifying strong-UV windows found. No notification sent.")
        return

    # Keep the strongest qualifying hour for each location and date.
    best = {}
    for match in matches:
        key = (match["location"], match["time"].date())
        if key not in best or match["uv"] > best[key]["uv"]:
            best[key] = match

    lines = []
    for match in sorted(best.values(), key=lambda item: item["time"]):
        lines.append(
            f'{match["location"]}: '
            f'{match["time"].strftime("%a, %b %d at %-I %p")} — '
            f'UV {match["uv"]:.1f}, clouds {match["cloud"]}%, '
            f'rain chance {match["rain"]}%, '
            f'{match["temperature"]:.0f}°F'
        )

    message = (
        "Potential strong-UV windows in the next 3 days:\n\n"
        + "\n".join(lines)
        + f"\n\nDashboard: {DASHBOARD_URL}"
        + "\nUV 6+ is high exposure risk. Use sun protection; "
          "these conditions do not mean tanning is safe."
    )

    request = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        headers={
            "Title": "Beach UV window found",
            "Priority": "default",
            "Tags": "sunny",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(
                f"ntfy returned HTTP status {response.status}"
            )

    print(f"Sent notification with {len(best)} qualifying windows.")


if __name__ == "__main__":
    main()
