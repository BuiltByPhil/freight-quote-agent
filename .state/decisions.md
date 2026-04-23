# Decisions Log

## 2026-04-23 — src/tools.py initial implementation

### D001: Project created from scratch
**Context:** Neither `skills/career.md` nor `.state/context.md` existed at task start. The
home directory contained only a `utility-comparator` project (utility-bill parser, unrelated).
**Decision:** Created `/Users/auraaisystems/freight-agent/` as the project root and initialised
a git repo there. All relative paths (`src/`, `.state/`, `skills/`) resolve within that root.
**Why:** The task required a git commit at the end; the home directory was not a git repo, so a
dedicated project directory was the cleanest approach.

### D002: Cubic weight divisor — 250 kg/m³
**Decision:** Used the 250 kg/m³ (volumetric factor) standard adopted by Toll, StarTrack,
Couriers Please, and TNT Australia for domestic road freight.
**Why:** The 250 factor is the Australian domestic road standard. Air freight typically uses
167 kg/m³; since no mode was specified the road default was applied.

### D003: Mock carrier set
**Decision:** Mocked five carriers: Toll IPEC (Road Express), StarTrack (Express), Couriers
Please (Standard), TNT Australia (Road Express), Sendle (Standard Parcel).
**Why:** These five cover the dominant market segments — enterprise road (Toll, TNT), Australia
Post premium (StarTrack), budget parcel (Couriers Please), tech-native (Sendle).

### D004: No FX conversion in format_quote_response
**Decision:** `format_quote_response` labels amounts with the requested currency symbol but does
not convert the numeric `price_aud` value.
**Why:** Real FX conversion requires a live rate feed (RBA or third-party). The comment in the
docstring documents exactly where that call would go. Silently converting with a hardcoded rate
would be misleading in production.

### D005: Error handling strategy
**Decision:** Specific except clauses (`ValueError`, `TypeError`, `KeyError`, `re.error`) rather
than bare `except` or `except Exception` in the first two tools. `format_quote_response` uses
`except Exception` as a final safety net only after more specific clauses because the enrichment
loop touches arbitrary dict values from external input.
**Why:** The task prohibits bare excepts. Specific clauses give actionable error messages. The
broad final catch in tool 3 prevents an unhandled exception from surfacing to the LLM caller.

### D006: validate_address uses heuristic regex, not GNAF
**Decision:** Implemented address parsing with `re` (state abbreviation + 4-digit postcode
extraction, heuristic suburb/street split on commas).
**Why:** GNAF and the AusPost Address Confidence API both require paid API keys. The docstring
comment documents both real endpoints. The mock is accurate enough to test the contract and
validate the tool schema.
