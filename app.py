
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import calculators as calc
import data_store as ds
from calculators import inr

st.set_page_config(page_title="FuelMitra", page_icon="⛽", layout="wide")
st.title("⛽FuelMitra")
st.caption("All amounts in ₹ | distance in km | petrol/diesel in litres | CNG in kg | EV in kWh")

prices = ds.load_prices()
FUELS = list(calc.FUEL_UNIT)
PRICE_COL = {"Petrol": "petrol_per_l", "Diesel": "diesel_per_l",
             "CNG": "cng_per_kg", "Electric": "electricity_per_kwh"}

# ---- Sidebar ----
city = st.sidebar.selectbox("City (for fuel prices)", prices["city"])
row = prices[prices["city"] == city].iloc[0]
autofill = st.sidebar.checkbox("Auto-fill fuel price from city", value=True,
                               help="Untick to enter every price yourself")
st.sidebar.markdown("**City prices (edit data/fuel_prices.csv)**")
for f in FUELS:
    st.sidebar.write(f"{f}: ₹{row[PRICE_COL[f]]:.2f} {calc.PRICE_UNIT[f].replace('₹', '')}")


# ---- Helpers ----
def num(label, key, min_value=0.0, step=None, value=None):
    """Number box that starts empty (returns None until the user types)."""
    return st.number_input(label, min_value=min_value, value=value, step=step,
                           placeholder="Enter value", key=key)


def price_box(fuel, key):
    """Fuel price box. Pre-filled from the city table only if auto-fill is ticked."""
    default = float(row[PRICE_COL[fuel]]) if autofill else None
    return st.number_input(f"Price ({calc.PRICE_UNIT[fuel]})", min_value=0.0, value=default,
                           placeholder="Enter price", key=f"{key}_{fuel}_{city}_{autofill}")


def ready(*vals):
    return all(v is not None and v > 0 for v in vals)


def wait():
    st.info("Enter all the values above to see the result.")


def safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except (ValueError, ZeroDivisionError) as e:
        st.error(str(e))
        return None


tabs = st.tabs(["Mileage & Trip", "Running Cost", "Compare Vehicles", "EV vs Fuel",
                "CO₂ Emissions", "Ownership Cost", "Fuel Log"])

# ---- 1. Mileage & trip ----
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Mileage calculator")
        d = num("Distance travelled (km)", "m_d")
        f = num("Fuel used (litres / kg / kWh)", "m_f")
        if ready(d, f):
            st.metric("Mileage", f"{calc.mileage(d, f):.2f} km per unit")
        else:
            wait()
    with c2:
        st.subheader("Trip cost")
        fuel = st.selectbox("Fuel type", FUELS, key="t_fuel")
        dist = num("Trip distance (km)", "t_d")
        eff = num(f"Efficiency ({calc.FUEL_UNIT[fuel]})", "t_e")
        pr = price_box(fuel, "t_p")
        if ready(dist, eff, pr):
            st.metric("Trip cost", inr(calc.trip_cost(dist, eff, pr), 2))
            st.write(f"Fuel needed: **{dist / eff:.1f}** units | Cost per km: **{inr(pr / eff, 2)}**")
        else:
            wait()

# ---- 2. Running cost ----
with tabs[1]:
    st.subheader("Monthly & yearly running cost")
    c1, c2, c3 = st.columns(3)
    fuel = c1.selectbox("Fuel type", FUELS, key="r_fuel")
    with c1:
        eff = num(f"Efficiency ({calc.FUEL_UNIT[fuel]})", "r_e")
        pr = price_box(fuel, "r_p")
    with c2:
        kmd = num("Km per day", "r_kmd")
        days = num("Days used per month", "r_days", min_value=1, step=1)
    with c3:
        if ready(eff, pr, kmd, days) and days <= 31:
            r = calc.running_cost(kmd, days, eff, pr)
            st.metric("Cost per km", inr(r["cost_per_km"], 2))
            st.metric("Monthly cost", inr(r["monthly_cost"]))
            st.metric("Yearly cost", inr(r["yearly_cost"]))
        else:
            wait()

# ---- 3. Compare vehicles ----
with tabs[2]:
    st.subheader("Compare up to 4 vehicles")
    mkm = num("Monthly distance (km)", "c_km")
    n = st.slider("Number of vehicles", 2, 4, 2)
    cols = st.columns(n)
    vehicles, complete = [], True
    for i, col in enumerate(cols):
        with col:
            name = st.text_input("Name", f"Vehicle {i + 1}", key=f"cn{i}")
            fuel = st.selectbox("Fuel", FUELS, index=i, key=f"cf{i}")
            eff = num(f"Efficiency ({calc.FUEL_UNIT[fuel]})", f"ce{i}")
            pr = price_box(fuel, f"cp{i}")
            if not ready(eff, pr):
                complete = False
            vehicles.append({"name": f"{name} ({fuel})", "efficiency": eff, "price_per_unit": pr})
    if complete and ready(mkm):
        res = calc.compare_vehicles(vehicles, mkm)
        df = pd.DataFrame(res)
        st.success(f"Cheapest to run: **{res[0]['name']}**, saves "
                   f"**{inr(res[0]['yearly_saving_vs_costliest'])}/year** vs the costliest.")
        show = df.assign(cost_per_km=df.cost_per_km.round(2),
                         monthly_cost=df.monthly_cost.round(0),
                         yearly_cost=df.yearly_cost.round(0))
        st.dataframe(show, hide_index=True, use_container_width=True)
        st.plotly_chart(px.bar(df, x="name", y="yearly_cost", text_auto=".3s",
                               labels={"yearly_cost": "Yearly fuel cost (₹)", "name": ""}),
                        use_container_width=True)
    else:
        wait()

# ---- 4. EV vs fuel ----
with tabs[3]:
    st.subheader("EV vs Petrol/Diesel/CNG break-even")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Fuel car**")
        ice_fuel = st.selectbox("Fuel", ["Petrol", "Diesel", "CNG"])
        ice_price = num("On-road price (₹)", "ip", step=10000.0)
        ice_eff = num(f"Efficiency ({calc.FUEL_UNIT[ice_fuel]})", "ie")
        ice_fp = price_box(ice_fuel, "ifp")
    with c2:
        st.markdown("**Electric car**")
        ev_price = num("On-road price (₹)", "ep", step=10000.0)
        ev_eff = num("Efficiency (km/kWh)", "ee")
        ev_fp = price_box("Electric", "efp")
    mk = num("Monthly distance (km)", "evkm")
    if ready(ice_price, ice_eff, ice_fp, ev_price, ev_eff, ev_fp, mk):
        ice_cpk, ev_cpk = ice_fp / ice_eff, ev_fp / ev_eff
        b = calc.break_even(ev_price - ice_price, ev_cpk, ice_cpk, mk)
        m1, m2, m3 = st.columns(3)
        m1.metric("Fuel car cost/km", inr(ice_cpk, 2))
        m2.metric("EV cost/km", inr(ev_cpk, 2))
        m3.metric("Saving per km", inr(b["saving_per_km"], 2))
        if b["km"] is None:
            st.warning("With these inputs the EV never pays back its extra price.")
        else:
            st.success(f"Break-even after **{b['km']:,.0f} km** (about "
                       f"**{b['months'] / 12:.1f} years** at {mk:,.0f} km/month).")
            years = list(range(0, 11))
            gap = [(ev_price - ice_price) - b["saving_per_km"] * mk * 12 * y for y in years]
            fig = px.line(x=years, y=gap, labels={"x": "Years", "y": "EV extra cost remaining (₹)"})
            fig.add_hline(y=0, line_dash="dash")
            st.plotly_chart(fig, use_container_width=True)
    else:
        wait()

# ---- 5. CO2 ----
with tabs[4]:
    st.subheader("CO₂ emissions")
    fuel = st.selectbox("Fuel type", FUELS, key="co_f")
    eff = num(f"Efficiency ({calc.FUEL_UNIT[fuel]})", "co_e")
    yk = num("Distance per year (km)", "co_k")
    if ready(eff, yk):
        co2 = calc.co2_for_distance(fuel, yk, eff)
        c1, c2, c3 = st.columns(3)
        c1.metric("CO₂ per year", f"{co2:,.0f} kg")
        c2.metric("CO₂ per km", f"{co2 / yk * 1000:.0f} g/km")
        c3.metric("Trees to offset", f"{calc.trees_to_offset(co2):,.0f}")
        comp = pd.DataFrame({"Fuel": FUELS,
                             "kg CO2/year": [calc.CO2_PER_UNIT[f] * yk / calc.FUEL_UNIT_DEFAULT[f]
                                             for f in FUELS]})
        st.caption("Chart compares typical efficiencies: petrol 16, diesel 20, CNG 26, EV 7")
        st.plotly_chart(px.bar(comp, x="Fuel", y="kg CO2/year", text_auto=".0f"),
                        use_container_width=True)
    else:
        wait()

# ---- 6. Ownership ----
with tabs[5]:
    st.subheader("Total cost of ownership")
    st.caption("Fields marked (optional) can be left empty; they count as 0.")
    c1, c2, c3 = st.columns(3)
    with c1:
        price = num("On-road price (₹)", "o_p", step=10000.0)
        down = num("Down payment (₹) (optional)", "o_down", step=10000.0)
        rate = num("Loan interest % p.a. (optional)", "o_rate")
        ly = num("Loan tenure in years (needed if loan)", "o_ly", min_value=1, step=1)
    with c2:
        fuel = st.selectbox("Fuel type", FUELS, key="o_f")
        eff = num(f"Efficiency ({calc.FUEL_UNIT[fuel]})", "o_e")
        fp = price_box(fuel, "o_fp")
        mk = num("Monthly km", "o_km")
    with c3:
        ins = num("Insurance per year (₹) (optional)", "o_ins")
        svc = num("Service per year (₹) (optional)", "o_svc")
        oy = num("Ownership period (years)", "o_oy", min_value=1, step=1)
        resale = num("Resale value % of price (optional)", "o_res")
    down, rate, ins, svc, resale = (v or 0 for v in (down, rate, ins, svc, resale))
    loan = max((price or 0) - down, 0)
    if ready(price, eff, fp, mk, oy) and (loan == 0 or ready(ly)) and resale <= 100:
        t = calc.total_cost_of_ownership(price, down, rate, ly or 0, mk, eff, fp,
                                         ins, svc, oy, resale)
        if loan > 0:
            st.info(f"Monthly EMI: **{inr(calc.emi(loan, rate, ly))}** for {ly} years")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total cost", inr(t["total"]))
        m2.metric("Per month", inr(t["per_month"]))
        m3.metric("Per km", inr(t["per_km"], 2))
        parts = pd.DataFrame({"Item": ["Vehicle", "Loan interest", "Fuel", "Insurance",
                                       "Service", "Resale (credit)"],
                              "Amount": [t["vehicle_price"], t["loan_interest"], t["fuel"],
                                         t["insurance"], t["service"], t["resale_value"]]})
        st.plotly_chart(px.bar(parts, x="Item", y="Amount", text_auto=".3s"),
                        use_container_width=True)
    else:
        wait()

# ---- 7. Fuel log ----
with tabs[6]:
    st.subheader("Fuel log tracker (full-tank method)")
    with st.form("log"):
        c1, c2, c3, c4 = st.columns(4)
        dt = c1.date_input("Date", date.today())
        odo = c2.number_input("Odometer (km)", min_value=0.0, value=None, step=1.0,
                              placeholder="Enter value")
        lt = c3.number_input("Litres filled", min_value=0.0, value=None, step=0.1,
                             placeholder="Enter value")
        pp = c4.number_input("Price (₹/l)", min_value=0.0,
                             value=float(row["petrol_per_l"]) if autofill else None,
                             step=0.1, placeholder="Enter value")
        if st.form_submit_button("Add fill-up"):
            if not ready(odo, lt, pp):
                st.error("Please fill odometer, litres and price.")
            else:
                try:
                    ds.add_entry(dt, odo, lt, pp)
                    st.success("Saved")
                except ValueError as e:
                    st.error(str(e))
    log = ds.load_log()
    if log.empty:
        st.info("No entries yet. Fill your tank to full each time and log it here.")
    else:
        d = ds.analyse(log)
        st.dataframe(d.round(2), hide_index=True, use_container_width=True)
        if d["mileage"].notna().any():
            valid = d.dropna(subset=["mileage"])
            k1, k2, k3 = st.columns(3)
            k1.metric("Average mileage", f"{valid.distance_km.sum() / valid.litres.sum():.1f} km/l")
            k2.metric("Total spent", inr(d["cost"].sum()))
            k3.metric("Avg cost per km", inr(valid.cost.sum() / valid.distance_km.sum(), 2))
            st.plotly_chart(px.line(valid, x="date", y="mileage", markers=True,
                                    labels={"mileage": "Mileage (km/l)"}),
                            use_container_width=True)
            ms = ds.monthly_summary(d)
            if not ms.empty:
                st.plotly_chart(px.bar(ms, y="spend", labels={"spend": "Monthly fuel spend (₹)",
                                                              "index": "Month"}),
                                use_container_width=True)
            for tip in ds.insights(d):
                st.write("💡 " + tip)
        st.download_button("Download log (CSV)", log.to_csv(index=False), "fuel_log.csv")