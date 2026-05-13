import requests


# coordinates
LAT = 28.4595
LON = 77.0266


class PaceAdjuster:
    def __init__(self, temp, humidity, dew_point, uv_index, wind_speed, is_acc=True):
        self.temp = temp
        self.humidity = humidity
        self.dew_point = dew_point
        self.uv = uv_index
        self.wind_speed = wind_speed
        self.is_acc = is_acc

    def calculate_heat_stress_score(self):

        base_stress = self.temp + (self.dew_point * 0.5)


        base_stress += (self.uv * 0.5)


        base_stress -= (self.wind_speed * 0.15)
        return base_stress

    def adjust_pace(self, base_pace_seconds):
        stress = self.calculate_heat_stress_score()


        if stress <= 20:
            return base_pace_seconds, 0


        penalty_rate = 0.008 if self.is_acc else 0.015

        degradation_factor = 1 + (stress - 20) * penalty_rate
        return base_pace_seconds * degradation_factor, (degradation_factor - 1) * 100

    def dehydration_risk(self, distance_km, pace_seconds):
        duration_hours = (distance_km * pace_seconds) / 3600


        sweat_rate = 0.5 + (self.temp * 0.02) + (self.dew_point * 0.015)


        sweat_rate = min(2.5, sweat_rate)

        total_fluid = sweat_rate * duration_hours
        risk_score = min(10, (sweat_rate * 3.0) + (self.uv * 0.4))
        return total_fluid, risk_score, duration_hours

    def get_hr_drift(self, hours, base_hr):
        stress = self.calculate_heat_stress_score()


        drift = 0.02 * hours


        if stress > 25:
            drift += (stress - 25) * 0.004 * hours

        if self.is_acc:
            drift *= 0.80

        final_hr = base_hr * (1 + drift)
        decoupling_pct = drift * 100
        return final_hr, decoupling_pct


def format_pace(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def main():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": "temperature_2m,relative_humidity_2m,dew_point_2m,uv_index,wind_speed_10m",
        "timezone": "auto"
    }

    try:
        print("fetching localized weather telemetry...")
        response = requests.get(url, params=params).json()
        current = response['current']
        t = current['temperature_2m']
        h = current['relative_humidity_2m']
        dp = current['dew_point_2m']
        uv = current['uv_index']
        wind = current['wind_speed_10m']

        print(f"\n--- CONDITIONS: {t}°C | Dew Point: {dp}°C | UV: {uv} | Wind: {wind}km/h ---")

        # 2. Input with Smart Defaults
        dist_in = input("distance (km) [default 5.0]: ")
        dist = float(dist_in) if dist_in else 5.0

        p_min_in = input("target pace (min) [default 5]: ")
        p_min = float(p_min_in) if p_min_in else 5.0

        p_sec_in = input("target pace (sec) [default 54]: ")
        p_sec = float(p_sec_in) if p_sec_in else 30.0

        hr_in = input("target HR (e.g. 145) [default 145]: ")
        hr = float(hr_in) if hr_in else 145.0

        acc_in = input("heat adapted? (y/n) [default y]: ")
        is_acc = False if acc_in.lower() == 'n' else True

        base_sec = (p_min * 60) + p_sec

        # 3. Execution
        runner = PaceAdjuster(t, h, dp, uv, wind, is_acc)

        adj_pace, penalty = runner.adjust_pace(base_sec)
        fluid, risk, hours = runner.dehydration_risk(dist, adj_pace)
        final_hr, decoupling = runner.get_hr_drift(hours, hr)

        print("\n" + "=" * 35)
        print(f"ADJUSTED PACE: {format_pace(adj_pace)}/km (+{penalty:.1f}%)")
        print(f"WATER NEEDED:  {fluid:.2f} Liters")
        print(f"THERMAL RISK:  {risk:.1f}/10")
        print("-" * 35)
        print(f"END-RUN HR:    ~{int(final_hr)} BPM")


        if decoupling > 5.0:
            print(f">> ALERT: {decoupling:.1f}% Aerobic Decoupling.")
            print(">> you will likely cross out of your target HR zone.")
        else:
            print(f">> HR Drift stable at {decoupling:.1f}%.")
        print("=" * 35)

    except Exception as e:
        print(f"Error fetching weather: {e}")


if __name__ == "__main__":
    main()