"""Tests for src/tools.py freight tool definitions."""

import pytest
from src.tools import get_carrier_rates, validate_address, format_quote_response


class TestGetCarrierRates:
    def test_happy_path_returns_success(self):
        result = get_carrier_rates(
            origin="Sydney",
            destination="Melbourne",
            weight_kg=5.0,
            dimensions={"length_cm": 30, "width_cm": 20, "height_cm": 15},
        )
        assert result["success"] is True
        assert len(result["carriers"]) > 0
        assert result["weight_kg"] == 5.0
        assert "cubic_weight_kg" in result
        assert "chargeable_weight_kg" in result

    def test_cubic_weight_calculation(self):
        # 100x100x100 cm = 1 m³ → 250 kg cubic weight
        result = get_carrier_rates(
            origin="Brisbane",
            destination="Perth",
            weight_kg=1.0,
            dimensions={"length_cm": 100, "width_cm": 100, "height_cm": 100},
        )
        assert result["success"] is True
        assert result["cubic_weight_kg"] == 250.0
        assert result["chargeable_weight_kg"] == 250.0

    def test_actual_weight_dominates_when_heavier(self):
        result = get_carrier_rates(
            origin="Adelaide",
            destination="Darwin",
            weight_kg=100.0,
            dimensions={"length_cm": 10, "width_cm": 10, "height_cm": 10},
        )
        assert result["success"] is True
        assert result["chargeable_weight_kg"] == 100.0

    def test_zero_weight_returns_error(self):
        result = get_carrier_rates(
            origin="Sydney",
            destination="Hobart",
            weight_kg=0.0,
            dimensions={"length_cm": 10, "width_cm": 10, "height_cm": 10},
        )
        assert result["success"] is False
        assert result["error"] is not None

    def test_negative_weight_returns_error(self):
        result = get_carrier_rates(
            origin="Sydney",
            destination="Hobart",
            weight_kg=-5.0,
            dimensions={"length_cm": 10, "width_cm": 10, "height_cm": 10},
        )
        assert result["success"] is False

    def test_missing_dimension_key_returns_error(self):
        result = get_carrier_rates(
            origin="Sydney",
            destination="Hobart",
            weight_kg=5.0,
            dimensions={"length_cm": 10, "width_cm": 10},  # missing height_cm
        )
        assert result["success"] is False
        assert "error" in result

    def test_all_carrier_prices_are_positive(self):
        result = get_carrier_rates(
            origin="Melbourne",
            destination="Sydney",
            weight_kg=2.0,
            dimensions={"length_cm": 20, "width_cm": 15, "height_cm": 10},
        )
        assert result["success"] is True
        for carrier in result["carriers"]:
            assert carrier["price_aud"] > 0

    def test_each_carrier_has_required_keys(self):
        result = get_carrier_rates(
            origin="Sydney",
            destination="Brisbane",
            weight_kg=3.0,
            dimensions={"length_cm": 25, "width_cm": 20, "height_cm": 15},
        )
        assert result["success"] is True
        required_keys = {
            "carrier", "service", "transit_days", "price_aud",
            "fuel_surcharge_pct", "estimated_delivery",
        }
        for carrier in result["carriers"]:
            assert required_keys.issubset(carrier.keys())

    def test_returns_five_carriers(self):
        result = get_carrier_rates(
            origin="Sydney",
            destination="Canberra",
            weight_kg=10.0,
            dimensions={"length_cm": 40, "width_cm": 30, "height_cm": 20},
        )
        assert result["success"] is True
        assert len(result["carriers"]) == 5

    def test_origin_and_destination_preserved(self):
        result = get_carrier_rates(
            origin="2000",
            destination="3000",
            weight_kg=1.0,
            dimensions={"length_cm": 10, "width_cm": 10, "height_cm": 10},
        )
        assert result["origin"] == "2000"
        assert result["destination"] == "3000"


class TestValidateAddress:
    def test_valid_sydney_address(self):
        result = validate_address("42 Wallaby Way, Sydney NSW 2000")
        assert result["valid"] is True
        assert result["components"]["state"] == "NSW"
        assert result["components"]["postcode"] == "2000"

    def test_valid_melbourne_address(self):
        result = validate_address("100 Collins Street, Melbourne VIC 3000")
        assert result["valid"] is True
        assert result["components"]["state"] == "VIC"
        assert result["components"]["postcode"] == "3000"

    def test_missing_postcode_is_invalid(self):
        result = validate_address("100 Collins Street Melbourne VIC")
        assert result["valid"] is False
        assert any("postcode" in e.lower() for e in result["errors"])

    def test_missing_state_is_invalid(self):
        result = validate_address("100 Collins Street Melbourne 3000")
        assert result["valid"] is False
        assert any("state" in e.lower() for e in result["errors"])

    def test_empty_string_is_invalid(self):
        result = validate_address("   ")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_non_string_returns_invalid_not_exception(self):
        result = validate_address(None)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_normalisation_uppercases_input(self):
        result = validate_address("42 Pitt Street, Sydney nsw 2000")
        assert result["valid"] is True
        assert "NSW" in result["normalised"]

    def test_postcode_state_mismatch_generates_warning(self):
        # Melbourne postcode (3000) claimed as NSW
        result = validate_address("100 Fake Street, Somewhere NSW 3000")
        assert any("3000" in w or "VIC" in w for w in result["warnings"])

    def test_act_address(self):
        result = validate_address("1 Constitution Avenue, Canberra ACT 2600")
        assert result["valid"] is True
        assert result["components"]["state"] == "ACT"

    def test_components_has_all_required_keys(self):
        result = validate_address("1 George Street, Brisbane QLD 4000")
        assert result["valid"] is True
        for key in ("street", "suburb", "state", "postcode", "country"):
            assert key in result["components"]
        assert result["components"]["country"] == "AU"

    def test_qld_address(self):
        result = validate_address("123 Eagle Street, Brisbane QLD 4000")
        assert result["valid"] is True
        assert result["components"]["state"] == "QLD"
        assert result["components"]["postcode"] == "4000"

    def test_wa_address(self):
        result = validate_address("45 St Georges Terrace, Perth WA 6000")
        assert result["valid"] is True
        assert result["components"]["state"] == "WA"


class TestFormatQuoteResponse:
    SAMPLE_RATES = [
        {
            "carrier": "Toll IPEC",
            "service": "Road Express",
            "price_aud": 28.50,
            "transit_days": 3,
            "estimated_delivery": "2026-04-26",
        },
        {
            "carrier": "StarTrack",
            "service": "Express",
            "price_aud": 22.00,
            "transit_days": 2,
            "estimated_delivery": "2026-04-25",
        },
        {
            "carrier": "Sendle",
            "service": "Standard Parcel",
            "price_aud": 18.00,
            "transit_days": 5,
            "estimated_delivery": "2026-04-28",
        },
    ]

    def test_quotes_sorted_cheapest_first(self):
        result = format_quote_response(self.SAMPLE_RATES)
        assert result["success"] is True
        prices = [q["price_aud"] for q in result["quotes"]]
        assert prices == sorted(prices)

    def test_recommended_is_cheapest(self):
        result = format_quote_response(self.SAMPLE_RATES)
        assert result["recommended"]["carrier"] == "Sendle"

    def test_fastest_has_lowest_transit_days(self):
        result = format_quote_response(self.SAMPLE_RATES)
        assert result["fastest"]["carrier"] == "StarTrack"
        assert result["fastest"]["transit_days"] == 2

    def test_aud_currency_symbol(self):
        result = format_quote_response(self.SAMPLE_RATES, currency="AUD")
        assert result["currency"] == "AUD"
        for q in result["quotes"]:
            assert q["display_price"].startswith("A$")

    def test_usd_currency_symbol(self):
        result = format_quote_response(self.SAMPLE_RATES, currency="USD")
        assert result["currency"] == "USD"
        for q in result["quotes"]:
            assert q["display_price"].startswith("US$")

    def test_rank_is_sequential_from_one(self):
        result = format_quote_response(self.SAMPLE_RATES)
        ranks = [q["rank"] for q in result["quotes"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_empty_list_returns_success_with_no_options(self):
        result = format_quote_response([])
        assert result["success"] is True
        assert result["total_options"] == 0
        assert result["recommended"] is None
        assert result["fastest"] is None

    def test_non_list_input_returns_error(self):
        result = format_quote_response("not a list")
        assert result["success"] is False
        assert result["error"] is not None

    def test_malformed_items_are_skipped(self):
        mixed = [
            {
                "carrier": "Toll",
                "price_aud": 30.0,
                "transit_days": 3,
                "service": "X",
                "estimated_delivery": "2026-04-26",
            },
            "not a dict",
            {"no_price": True},
        ]
        result = format_quote_response(mixed)
        assert result["success"] is True
        assert result["total_options"] == 1

    def test_generated_at_ends_with_z(self):
        result = format_quote_response(self.SAMPLE_RATES)
        assert result["generated_at"].endswith("Z")

    def test_total_options_matches_valid_quote_count(self):
        result = format_quote_response(self.SAMPLE_RATES)
        assert result["total_options"] == 3
        assert len(result["quotes"]) == 3

    def test_currency_symbol_preserved_in_each_quote(self):
        result = format_quote_response(self.SAMPLE_RATES, currency="NZD")
        for q in result["quotes"]:
            assert q["currency_symbol"] == "NZ$"
