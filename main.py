import requests

# gurgaon coords
LAT = 28.4595
LON = 77.0266


class PaceAdjuster:
    def __init__(self, temp, humidity, uv_index, wind_speed):
        self.temp = temp
        self.humidity = humidity
        self.uv = uv_index
        self.wind_speed = wind_speed

    def calculate_wbgt_approx(self):
        # 0.7*WetBulb + 0.2*BlackGlobe + 0.1*DryBulb

        rh_factor = self.humidity / 100
        wbgt = (0.567 * self.temp) + (0.399 * self.temp * rh_factor) + 3.94

        # solar radiation
        wbgt += (self.uv * 0.6)

        # wind cools
        wbgt -= (self.wind_speed * 0.15)

        return wbgt

    def adjust_pace(self, base_pace_seconds):
        wbgt = self.calculate_wbgt_approx()
        if wbgt <= 18:
            return base_pace_seconds, 0

        # ~1.8% less/km after 18
        degradation_factor = 1 + (wbgt - 18) * 0.018
        return base_pace_seconds * degradation_factor, (degradation_factor - 1) * 100

    def dehydration_risk(self, distance_km, pace_seconds):
        duration_hours = (distance_km * pace_seconds) / 3600

        # wind increases evap. rate
        sweat_rate = 0.6 + (self.temp * 0.025) + (self.humidity * 0.008) + (self.wind_speed * 0.005)

        total_fluid = sweat_rate * duration_hours
        risk_score = min(10, (sweat_rate * 3.5) + (self.uv / 2))
        return total_fluid, risk_score


def format_pace(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def main():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": "temperature_2m,relative_humidity_2m,uv_index,wind_speed_10m",
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params).json()
        current = response['current']
        t = current['temperature_2m']
        h = current['relative_humidity_2m']
        uv = current['uv_index']
        wind = current['wind_speed_10m']

        print(f"--- Gurugram Live: {t}°C | {h}% Humidity | UV: {uv} | Wind: {wind}km/h ---")

        # 2. Input
        dist = float(input("Distance (km): "))
        p_min = float(input("Target Pace (min): "))
        p_sec = float(input("Target Pace (sec): "))

        base_sec = (p_min * 60) + p_sec

        runner = PaceAdjuster(t, h, uv, wind)
        adj_pace, penalty = runner.adjust_pace(base_sec)
        fluid, risk = runner.dehydration_risk(dist, adj_pace)

        print("\n" + "=" * 30)
        print(f"ADJUSTED PACE: {format_pace(adj_pace)}/km (+{penalty:.1f}%)")
        print(f"WATER NEEDED:  {fluid:.2f} Liters")
        print(f"THERMAL RISK:  {risk:.1f}/10")
        print("=" * 30)

    except Exception as e:
        print(f"Error fetching weather: {e}")


if __name__ == "__main__":
    main()