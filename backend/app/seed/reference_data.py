"""Static reference data: exchange rates and per-country salary bands.

These are the fixed inputs the seed script and tests share. Rates are integer
micro-USD per one unit of the currency (``ADR-0006``); pay bands are illustrative
local-currency ranges per level, sized to each country's currency so generated data
looks plausible (a JPY salary is in the millions, an INR salary in the lakhs).
"""

from __future__ import annotations

# ISO 4217 -> micro-USD per one unit of the currency. Approximate mid-decade rates;
# the point is plausible, deterministic normalization, not live accuracy.
DEFAULT_FX_RATES_MICROS: dict[str, int] = {
    "USD": 1_000_000,
    "EUR": 1_080_000,
    "GBP": 1_270_000,
    "INR": 12_000,
    "CAD": 730_000,
    "AUD": 660_000,
    "SGD": 740_000,
    "BRL": 200_000,
    "AED": 272_000,
    "ZAR": 54_000,
    "JPY": 6_700,
}

# Per-currency base annual salary for level L1, in local major units. Higher levels
# scale this up (see LEVEL_MULTIPLIERS). Chosen so cross-country pay is comparable
# once normalized to USD.
L1_BASE_SALARY_BY_CURRENCY: dict[str, int] = {
    "USD": 70_000,
    "EUR": 60_000,
    "GBP": 55_000,
    "INR": 1_200_000,
    "CAD": 85_000,
    "AUD": 90_000,
    "SGD": 80_000,
    "BRL": 200_000,
    "AED": 220_000,
    "ZAR": 700_000,
    "JPY": 6_500_000,
}

# Level -> multiplier applied to the L1 base salary.
LEVEL_MULTIPLIERS: dict[str, float] = {
    "L1": 1.0,
    "L2": 1.35,
    "L3": 1.8,
    "L4": 2.4,
    "L5": 3.2,
    "L6": 4.3,
    "L7": 5.8,
}
