# FuelMitra

A fuel and vehicle cost calculator built for Indian users. You enter your vehicle details and it works out what you actually spend per km, per month and over the years of owning the vehicle.

Everything uses Indian units: ₹ for money, km for distance, litres for petrol and diesel, kg for CNG and kWh for EVs.

## What it does

- Mileage and trip cost
- Daily, monthly and yearly running cost
- Side by side comparison of petrol, diesel, CNG and EV
- EV vs fuel car break-even (in km and years)
- CO₂ emissions per year
- Total cost of ownership with loan EMI, insurance, service and resale value
- Fuel log that saves fill-ups and shows mileage trends and monthly spend
- City-wise fuel prices from a CSV file



## Tech used

Python, Streamlit, Pandas, Plotly

## How to run

```bash
git clone https://github.com/YOUR-USERNAME/FuelMitra.git
cd FuelMitra
pip install -r requirements.txt
streamlit run app.py
```

To run the tests:

```bash
pytest
```

## How it's organised

```
FuelMitra/
├── app.py            # Streamlit interface
├── calculators.py    # all the formulas
├── data_store.py     # fuel log saving and analysis
├── data/
│   └── fuel_prices.csv
├── tests/
├── requirements.txt
└── README.md
```

## Formulas used

- Mileage = distance / fuel used
- Cost per km = fuel price / mileage
- EMI = P × r × (1+r)^n / ((1+r)^n − 1)
- EV break-even = extra purchase price / (fuel car cost per km − EV cost per km)
- CO₂ = fuel quantity × emission factor

## Notes

- The fuel prices in `data/fuel_prices.csv` are sample values. Update them with current rates before relying on the results.
- Emission factors are approximate averages (petrol 2.31 kg/l, diesel 2.68 kg/l, CNG 2.69 kg/kg, Indian grid about 0.82 kg/kWh).