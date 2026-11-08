import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from calculators import *


def test_mileage():
    assert mileage(300, 15) == 20


def test_trip_cost():
    assert trip_cost(100, 20, 100) == 500


def test_running_cost():
    r = running_cost(30, 26, 15, 100)
    assert round(r["monthly_cost"]) == 5200


def test_invalid_input():
    with pytest.raises(ValueError):
        mileage(100, 0)


def test_emi():
    assert round(emi(1_000_000, 9, 5)) == 20758


def test_break_even():
    b = break_even(300000, 1.0, 7.0, 1000)
    assert b["km"] == 50000 and b["months"] == 50


def test_break_even_never():
    assert break_even(100000, 8, 7, 1000)["km"] is None


def test_co2():
    assert round(co2_emissions("Petrol", 10), 1) == 23.1


def test_inr_format():
    assert inr(1234567) == "₹12,34,567"
    assert inr(950) == "₹950"
    assert inr(100000) == "₹1,00,000"
