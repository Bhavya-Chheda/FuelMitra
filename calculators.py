"""Core formulas for the Smart Fuel & Vehicle Cost Analyzer (India).

Units: distance in km, petrol/diesel in litres, CNG in kg,
electricity in kWh, money in Indian Rupees (INR).
"""

# CO2 emission factors
CO2_PER_UNIT = {
    "Petrol": 2.31,    # kg CO2 per litre
    "Diesel": 2.68,    # kg CO2 per litre
    "CNG": 2.69,       # kg CO2 per kg
    "Electric": 0.82,  # kg CO2 per kWh (approx. Indian grid average)
}
FUEL_UNIT = {"Petrol": "km/l", "Diesel": "km/l", "CNG": "km/kg", "Electric": "km/kWh"}
PRICE_UNIT = {"Petrol": "₹/l", "Diesel": "₹/l", "CNG": "₹/kg", "Electric": "₹/kWh"}


def _positive(**kwargs):
    for name, value in kwargs.items():
        if value is None or value <= 0:
            raise ValueError(f"{name} must be greater than 0")


def mileage(distance_km, fuel_used):
    """Efficiency = distance / fuel (km/l, km/kg or km/kWh)."""
    _positive(distance_km=distance_km, fuel_used=fuel_used)
    return distance_km / fuel_used


def trip_cost(distance_km, efficiency, price_per_unit):
    """Cost of a single trip in INR."""
    _positive(distance_km=distance_km, efficiency=efficiency, price_per_unit=price_per_unit)
    return (distance_km / efficiency) * price_per_unit


def cost_per_km(efficiency, price_per_unit):
    _positive(efficiency=efficiency, price_per_unit=price_per_unit)
    return price_per_unit / efficiency


def running_cost(km_per_day, days_per_month, efficiency, price_per_unit):
    """Returns dict with cost per km, monthly and yearly running cost."""
    _positive(km_per_day=km_per_day, days_per_month=days_per_month)
    cpk = cost_per_km(efficiency, price_per_unit)
    monthly_km = km_per_day * days_per_month
    return {
        "cost_per_km": cpk,
        "monthly_km": monthly_km,
        "monthly_cost": cpk * monthly_km,
        "yearly_cost": cpk * monthly_km * 12,
    }


def compare_vehicles(vehicles, monthly_km):
    """vehicles: list of dicts {name, efficiency, price_per_unit}.
    Returns list sorted cheapest first, with savings vs the costliest."""
    _positive(monthly_km=monthly_km)
    rows = []
    for v in vehicles:
        cpk = cost_per_km(v["efficiency"], v["price_per_unit"])
        rows.append({"name": v["name"], "cost_per_km": cpk,
                     "monthly_cost": cpk * monthly_km,
                     "yearly_cost": cpk * monthly_km * 12})
    rows.sort(key=lambda r: r["monthly_cost"])
    worst = rows[-1]["yearly_cost"]
    for r in rows:
        r["yearly_saving_vs_costliest"] = worst - r["yearly_cost"]
    return rows


def co2_emissions(fuel_type, quantity):
    """kg CO2 for given quantity (litres / kg / kWh)."""
    _positive(quantity=quantity)
    return CO2_PER_UNIT[fuel_type] * quantity


def co2_for_distance(fuel_type, distance_km, efficiency):
    _positive(distance_km=distance_km, efficiency=efficiency)
    return co2_emissions(fuel_type, distance_km / efficiency)


def trees_to_offset(co2_kg_per_year, kg_per_tree=21):
    """Approx. trees needed to absorb the yearly CO2 (about 21 kg/tree/year)."""
    return co2_kg_per_year / kg_per_tree


def break_even(extra_price, ev_cost_per_km, ice_cost_per_km, monthly_km):
    """Break-even point of a costlier EV against a petrol/diesel/CNG car.
    Returns dict with km and months (None if EV never pays back)."""
    saving_per_km = ice_cost_per_km - ev_cost_per_km
    if saving_per_km <= 0:
        return {"saving_per_km": saving_per_km, "km": None, "months": None}
    if extra_price <= 0:
        return {"saving_per_km": saving_per_km, "km": 0, "months": 0}
    km = extra_price / saving_per_km
    return {"saving_per_km": saving_per_km, "km": km, "months": km / monthly_km}


def emi(principal, annual_rate_pct, years):
    """Monthly EMI = P*r*(1+r)^n / ((1+r)^n - 1)."""
    _positive(principal=principal, years=years)
    n = int(years * 12)
    if annual_rate_pct <= 0:
        return principal / n
    r = annual_rate_pct / 12 / 100
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def total_cost_of_ownership(on_road_price, down_payment, loan_rate_pct, loan_years,
                            monthly_km, efficiency, price_per_unit,
                            yearly_insurance, yearly_service, ownership_years,
                            resale_pct=40):
    """TCO over ownership_years, net of resale value (% of on-road price)."""
    _positive(on_road_price=on_road_price, ownership_years=ownership_years)
    loan = max(on_road_price - down_payment, 0)
    interest = 0.0
    if loan > 0:
        tenure = min(loan_years, ownership_years) if loan_years > 0 else ownership_years
        monthly_emi = emi(loan, loan_rate_pct, loan_years)
        interest = monthly_emi * loan_years * 12 - loan
    fuel = cost_per_km(efficiency, price_per_unit) * monthly_km * 12 * ownership_years
    insurance = yearly_insurance * ownership_years
    service = yearly_service * ownership_years
    resale = on_road_price * resale_pct / 100
    total = on_road_price + interest + fuel + insurance + service - resale
    return {"vehicle_price": on_road_price, "loan_interest": interest, "fuel": fuel,
            "insurance": insurance, "service": service, "resale_value": -resale,
            "total": total,
            "per_km": total / (monthly_km * 12 * ownership_years),
            "per_month": total / (ownership_years * 12)}


def inr(amount, decimals=0):
    """Format number Indian style: 1234567 -> ₹12,34,567."""
    neg = amount < 0
    amount = abs(amount)
    s = f"{amount:.{decimals}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    out = "₹" + whole + (("." + frac) if frac else "")
    return "-" + out if neg else out


# Typical efficiencies (km per unit) used only for the CO2 comparison chart
FUEL_UNIT_DEFAULT = {"Petrol": 16, "Diesel": 20, "CNG": 26, "Electric": 7}
