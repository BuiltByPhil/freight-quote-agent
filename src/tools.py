"""
Freight quote tool definitions for Australian carrier rate lookup,
address validation, and quote formatting.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Tool 1: get_carrier_rates
# ---------------------------------------------------------------------------

def get_carrier_rates(
    origin: str,
    destination: str,
    weight_kg: float,
    dimensions: dict,
) -> dict:
    """Retrieve freight rates from multiple Australian carriers for a given shipment.

    Args:
        origin: Origin suburb or postcode within Australia (e.g. "Sydney", "2000").
        destination: Destination suburb or postcode within Australia
                     (e.g. "Melbourne", "3000").
        weight_kg: Gross weight of the shipment in kilograms.
        dimensions: Carton dimensions with keys "length_cm", "width_cm", "height_cm"
                    (all floats/ints, in centimetres).

    Returns:
        dict with keys:
            "success" (bool): Whether the request completed without error.
            "origin" (str): Origin value passed in.
            "destination" (str): Destination value passed in.
            "weight_kg" (float): Weight as provided.
            "cubic_weight_kg" (float): Calculated volumetric weight.
            "chargeable_weight_kg" (float): Greater of actual and cubic weight.
            "carriers" (list[dict]): One entry per carrier, each containing:
                "carrier" (str), "service" (str), "transit_days" (int),
                "price_aud" (float), "fuel_surcharge_pct" (float),
                "estimated_delivery" (str, ISO-8601 date).
            "error" (str | None): Error message if success is False.

    Raises:
        ValueError: If weight_kg is non-positive or required dimension keys are missing.
    """
    # Real implementation would call carrier APIs, e.g.:
    #   Toll API:        POST https://api.toll.com.au/v2/freight/rates  (Basic Auth)
    #   StarTrack API:   POST https://digitalapi.auspost.com.au/shipping/price  (API key)
    #   Sendle API:      GET  https://api.sendle.com/api/quote  (Basic Auth)
    # Each response would be normalised into the "carriers" list returned below.

    try:
        if weight_kg <= 0:
            raise ValueError(f"weight_kg must be positive, got {weight_kg}")

        required_dim_keys = {"length_cm", "width_cm", "height_cm"}
        missing = required_dim_keys - set(dimensions.keys())
        if missing:
            raise ValueError(f"dimensions dict missing keys: {missing}")

        length_cm = float(dimensions["length_cm"])
        width_cm = float(dimensions["width_cm"])
        height_cm = float(dimensions["height_cm"])

        # Australian domestic road freight cubic weight factor: 250 kg/m³
        cubic_weight_kg = round(
            (length_cm * width_cm * height_cm) / 1_000_000 * 250, 3
        )
        chargeable_weight_kg = max(weight_kg, cubic_weight_kg)

        today = datetime.today()
        carriers: list[dict[str, Any]] = [
            {
                "carrier": "Toll IPEC",
                "service": "Road Express",
                "transit_days": 3,
                "price_aud": round(12.50 + chargeable_weight_kg * 2.80, 2),
                "fuel_surcharge_pct": 18.5,
                "estimated_delivery": (today + timedelta(days=3)).date().isoformat(),
            },
            {
                "carrier": "StarTrack",
                "service": "Express",
                "transit_days": 2,
                "price_aud": round(15.00 + chargeable_weight_kg * 3.20, 2),
                "fuel_surcharge_pct": 17.0,
                "estimated_delivery": (today + timedelta(days=2)).date().isoformat(),
            },
            {
                "carrier": "Couriers Please",
                "service": "Standard",
                "transit_days": 4,
                "price_aud": round(9.95 + chargeable_weight_kg * 2.40, 2),
                "fuel_surcharge_pct": 15.0,
                "estimated_delivery": (today + timedelta(days=4)).date().isoformat(),
            },
            {
                "carrier": "TNT Australia",
                "service": "Road Express",
                "transit_days": 3,
                "price_aud": round(13.75 + chargeable_weight_kg * 2.95, 2),
                "fuel_surcharge_pct": 19.0,
                "estimated_delivery": (today + timedelta(days=3)).date().isoformat(),
            },
            {
                "carrier": "Sendle",
                "service": "Standard Parcel",
                "transit_days": 5,
                "price_aud": round(8.50 + chargeable_weight_kg * 2.10, 2),
                "fuel_surcharge_pct": 0.0,
                "estimated_delivery": (today + timedelta(days=5)).date().isoformat(),
            },
        ]

        return {
            "success": True,
            "origin": origin,
            "destination": destination,
            "weight_kg": weight_kg,
            "cubic_weight_kg": cubic_weight_kg,
            "chargeable_weight_kg": chargeable_weight_kg,
            "carriers": carriers,
            "error": None,
        }

    except ValueError as exc:
        return {"success": False, "carriers": [], "error": str(exc)}
    except (TypeError, KeyError) as exc:
        return {"success": False, "carriers": [], "error": f"Invalid input: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: validate_address
# ---------------------------------------------------------------------------

_AU_STATES = frozenset({"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"})

# Postcode→state mapping for cross-validation (real validation uses GNAF or AusPost API)
_POSTCODE_STATE_RANGES: list[tuple[range, str]] = [
    (range(800, 1000), "NT"),
    (range(1000, 2000), "NSW"),
    (range(2000, 2600), "NSW"),
    (range(2600, 2620), "ACT"),
    (range(2620, 3000), "NSW"),
    (range(3000, 4000), "VIC"),
    (range(4000, 5000), "QLD"),
    (range(5000, 6000), "SA"),
    (range(6000, 7000), "WA"),
    (range(7000, 8000), "TAS"),
]


def validate_address(address_string: str) -> dict:
    """Validate and parse an Australian address string.

    Args:
        address_string: Free-form address string, e.g.
                        "42 Wallaby Way, Sydney NSW 2000" or
                        "Unit 3, 100 Collins Street Melbourne VIC 3000".

    Returns:
        dict with keys:
            "valid" (bool): True if the address passes basic structural validation.
            "normalised" (str): Cleaned, whitespace-collapsed, uppercased address.
            "components" (dict): Parsed fields — "street" (str), "suburb" (str),
                "state" (str), "postcode" (str), "country" (str, always "AU").
            "warnings" (list[str]): Non-fatal issues found during parsing.
            "errors" (list[str]): Fatal issues that make the address invalid.

    Raises:
        TypeError: If address_string is not a string (caught internally; returned
                   as an invalid result rather than propagated).
    """
    # Real implementation would call:
    #   Australia Post Address Confidence API:
    #     GET https://digitalapi.auspost.com.au/address-confidence/v1/details
    #         ?address=<url-encoded-address>   (requires AusPost API key)
    #   or the GNAF predictive geocoding service:
    #     POST https://api.psma.com.au/v1/predictive/address
    # Both return structured JSON with street number, street name, suburb, state, postcode.

    try:
        if not isinstance(address_string, str):
            raise TypeError(
                f"address_string must be str, got {type(address_string).__name__}"
            )

        address_string = address_string.strip()
        if not address_string:
            return {
                "valid": False,
                "normalised": "",
                "components": {},
                "warnings": [],
                "errors": ["Address string is empty."],
            }

        normalised = re.sub(r"\s+", " ", address_string).strip().upper()
        errors: list[str] = []
        warnings: list[str] = []

        # Extract postcode — 4-digit sequence at or near the end of the string
        postcode_match = re.search(r"\b(\d{4})\b", normalised)
        postcode = postcode_match.group(1) if postcode_match else ""
        if not postcode:
            errors.append("No 4-digit Australian postcode found.")

        # Extract state abbreviation
        state_match = re.search(r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b", normalised)
        state = state_match.group(1) if state_match else ""
        if not state:
            errors.append("No recognised Australian state abbreviation found.")

        # Cross-check postcode against expected state
        if postcode and state:
            pc_int = int(postcode)
            expected_state: str | None = None
            for pc_range, st in _POSTCODE_STATE_RANGES:
                if pc_int in pc_range:
                    expected_state = st
                    break
            if expected_state and expected_state != state:
                warnings.append(
                    f"Postcode {postcode} typically belongs to {expected_state}, not {state}."
                )

        # Heuristic: remove postcode and state, then split on commas for suburb/street
        remainder = normalised
        if postcode:
            remainder = remainder.replace(postcode, "").strip()
        if state:
            remainder = re.sub(rf"\b{state}\b", "", remainder).strip()
        remainder = remainder.strip(", ").strip()

        parts = [p.strip() for p in remainder.split(",") if p.strip()]
        suburb = parts[-1] if parts else ""
        street = ", ".join(parts[:-1]) if len(parts) > 1 else ""

        if not suburb:
            warnings.append("Could not determine suburb from address.")
        if not street:
            warnings.append("Could not determine street from address.")

        components = {
            "street": street,
            "suburb": suburb,
            "state": state,
            "postcode": postcode,
            "country": "AU",
        }

        return {
            "valid": len(errors) == 0,
            "normalised": normalised,
            "components": components,
            "warnings": warnings,
            "errors": errors,
        }

    except TypeError as exc:
        return {
            "valid": False,
            "normalised": "",
            "components": {},
            "warnings": [],
            "errors": [str(exc)],
        }
    except re.error as exc:
        return {
            "valid": False,
            "normalised": "",
            "components": {},
            "warnings": [],
            "errors": [f"Regex error during parsing: {exc}"],
        }


# ---------------------------------------------------------------------------
# Tool 3: format_quote_response
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOLS: dict[str, str] = {
    "AUD": "A$",
    "USD": "US$",
    "NZD": "NZ$",
    "GBP": "£",
    "EUR": "€",
}


def format_quote_response(
    rates_list: list,
    currency: str = "AUD",
) -> dict:
    """Format a list of raw carrier rate dicts into a structured freight quote response.

    Args:
        rates_list: List of carrier rate dicts, each expected to contain at minimum:
                    "carrier" (str), "service" (str), "price_aud" (float),
                    "transit_days" (int), "estimated_delivery" (str).
                    Additional keys are preserved as-is. Malformed items are skipped.
        currency: ISO-4217 currency code for display. Defaults to "AUD".
                  Note: this tool does *not* perform FX conversion; it labels
                  amounts with the given currency symbol only.

    Returns:
        dict with keys:
            "success" (bool): True if formatting completed without error.
            "currency" (str): The currency code used.
            "total_options" (int): Number of valid quotes included.
            "quotes" (list[dict]): Rates sorted cheapest-first, each enriched with:
                "rank" (int), "display_price" (str), "currency_symbol" (str).
            "recommended" (dict | None): The cheapest valid option (first in sorted list).
            "fastest" (dict | None): The option with the lowest transit_days.
            "generated_at" (str): ISO-8601 UTC timestamp when the response was formatted.
            "error" (str | None): Error message if success is False.

    Raises:
        TypeError: If rates_list is not a list (caught internally; returned as an
                   error result rather than propagated).
    """
    # Real implementation would also apply:
    #   - FX conversion via the Reserve Bank of Australia exchange rate feed:
    #       https://www.rba.gov.au/statistics/frequency/exchange-rates.html
    #   - GST itemisation (10% on freight services in Australia)
    #   - Carrier-specific surcharge breakdown from each carrier's billing API

    _currency = currency if isinstance(currency, str) else "AUD"

    try:
        if not isinstance(rates_list, list):
            raise TypeError(f"rates_list must be list, got {type(rates_list).__name__}")

        _currency = currency.upper().strip()
        currency_symbol = _CURRENCY_SYMBOLS.get(_currency, _currency)
        generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        valid_quotes: list[dict[str, Any]] = []
        for item in rates_list:
            if not isinstance(item, dict):
                continue
            if "price_aud" not in item or "carrier" not in item:
                continue
            try:
                float(item["price_aud"])
            except (TypeError, ValueError):
                continue
            valid_quotes.append(item)

        if not valid_quotes:
            return {
                "success": True,
                "currency": _currency,
                "total_options": 0,
                "quotes": [],
                "recommended": None,
                "fastest": None,
                "generated_at": generated_at,
                "error": None,
            }

        sorted_quotes = sorted(valid_quotes, key=lambda q: float(q["price_aud"]))

        enriched: list[dict[str, Any]] = []
        for rank, quote in enumerate(sorted_quotes, start=1):
            price = float(quote["price_aud"])
            enriched.append(
                {
                    **quote,
                    "rank": rank,
                    "display_price": f"{currency_symbol}{price:,.2f}",
                    "currency_symbol": currency_symbol,
                }
            )

        fastest = min(
            enriched,
            key=lambda q: int(q.get("transit_days", 9999)),
            default=None,
        )

        return {
            "success": True,
            "currency": _currency,
            "total_options": len(enriched),
            "quotes": enriched,
            "recommended": enriched[0],
            "fastest": fastest,
            "generated_at": generated_at,
            "error": None,
        }

    except TypeError as exc:
        return {
            "success": False,
            "currency": _currency,
            "total_options": 0,
            "quotes": [],
            "recommended": None,
            "fastest": None,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "success": False,
            "currency": _currency,
            "total_options": 0,
            "quotes": [],
            "recommended": None,
            "fastest": None,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "error": f"Unexpected error: {exc}",
        }
