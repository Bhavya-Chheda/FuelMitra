"""Fuel log storage (CSV) and analysis with Pandas."""
import os
import pandas as pd

LOG_PATH = os.path.join("data", "fuel_log.csv")
PRICE_PATH = os.path.join("data", "fuel_prices.csv")
COLUMNS = ["date", "odometer_km", "litres", "price_per_litre", "full_tank"]


def load_prices():
    return pd.read_csv(PRICE_PATH)


def load_log():
    if not os.path.exists(LOG_PATH):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(LOG_PATH, parse_dates=["date"])
    return df.sort_values("odometer_km").reset_index(drop=True)


def add_entry(date, odometer_km, litres, price_per_litre, full_tank=True):
    if litres <= 0 or price_per_litre <= 0 or odometer_km <= 0:
        raise ValueError("Odometer, litres and price must be greater than 0")
    df = load_log()
    if not df.empty and odometer_km <= df["odometer_km"].max():
        raise ValueError("Odometer must be higher than your last entry")
    row = pd.DataFrame([[pd.to_datetime(date), odometer_km, litres,
                         price_per_litre, full_tank]], columns=COLUMNS)
    os.makedirs("data", exist_ok=True)
    pd.concat([df, row], ignore_index=True).to_csv(LOG_PATH, index=False)


def analyse(df):
    """Adds distance, mileage, cost and cost/km columns (full-tank method)."""
    if len(df) < 2:
        return df.assign(distance_km=None, mileage=None, cost=None, cost_per_km=None)
    d = df.copy()
    d["distance_km"] = d["odometer_km"].diff()
    d["cost"] = d["litres"] * d["price_per_litre"]
    d["mileage"] = d["distance_km"] / d["litres"]
    d["cost_per_km"] = d["cost"] / d["distance_km"]
    return d


def monthly_summary(d):
    d = d.dropna(subset=["mileage"])
    if d.empty:
        return pd.DataFrame()
    g = d.groupby(d["date"].dt.to_period("M")).agg(
        km=("distance_km", "sum"), litres=("litres", "sum"),
        spend=("cost", "sum"))
    g["avg_mileage"] = g["km"] / g["litres"]
    g["cost_per_km"] = g["spend"] / g["km"]
    g.index = g.index.astype(str)
    return g


def insights(d):
    """Plain-English tips based on the latest fill-ups."""
    d = d.dropna(subset=["mileage"])
    tips = []
    if len(d) < 3:
        return ["Add at least 3 fill-ups to get insights."]
    last, prev_avg = d["mileage"].iloc[-1], d["mileage"].iloc[:-1].mean()
    change = (last - prev_avg) / prev_avg * 100
    if change <= -10:
        tips.append(f"Mileage dropped {abs(change):.0f}% vs your average. "
                    "Check tyre pressure, air filter and service due date.")
    elif change >= 10:
        tips.append(f"Mileage improved {change:.0f}% vs your average. Nice driving!")
    else:
        tips.append("Your mileage is stable compared to your average.")
    best, worst = d.loc[d["mileage"].idxmax()], d.loc[d["mileage"].idxmin()]
    tips.append(f"Best: {best['mileage']:.1f} km/l on {best['date']:%d %b %Y}. "
                f"Worst: {worst['mileage']:.1f} km/l on {worst['date']:%d %b %Y}.")
    return tips
