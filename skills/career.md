# Career Context

## Role
AI/automation engineer building freight quoting tools for Australian logistics operators.

## Domain
- Australian domestic freight: road express, air, parcel carriers
- Key carriers: Toll Group, StarTrack (AusPost), Couriers Please, TNT Australia, Sendle,
  Allied Express, Direct Couriers, Hunter Express
- Pricing model: chargeable weight = max(actual kg, cubic kg); cubic divisor 250 kg/m³
- Currency: AUD; GST applies at 10% on freight services
- Address standard: GNAF (Geocoded National Address File); AusPost Address Confidence API

## Goal
Build a Claude-powered freight quote agent that:
1. Retrieves rates from multiple carriers via their REST APIs
2. Validates Australian delivery addresses before quoting
3. Presents structured, ranked quotes to the user
