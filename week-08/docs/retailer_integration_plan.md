# Manufacturer-Retailer Integration Plan (Week 7)

## Overview
This document outlines the necessary changes in the **Manufacturer App** to support the integration with the newly created **Retailer App**. Currently, the Manufacturer lacks the wholesale capabilities and API endpoints expected by the Retailer.

## 1. API Endpoint Alignment

The Retailer's `ManufacturerClient` expects specific endpoints that do not currently match the Manufacturer's API structure.

| Feature | Retailer Expectation (URL) | Manufacturer Current (URL) | Action |
| :--- | :--- | :--- | :--- |
| **Catalog** | `GET /api/catalog` | *None* | **Create** endpoint to return SKUs and wholesale prices. |
| **Orders** | `POST /api/orders` | `POST /api/orders` | **Modify** to distinguish between internal and retailer orders. |
| **Order Status**| `GET /api/orders/{id}`| `GET /api/orders/{id}` | **Update** status mapping (Add `shipped`/`delivered`). |
| **Current Day** | `GET /api/day/current` | `GET /api/simulation/status` | **Create alias** or update path. |
| **Advance Day** | `POST /api/day/advance` | `POST /api/simulation/advance` | **Create alias** or update path. |

## 2. Wholesale Pricing Management

The Manufacturer currently lacks a database-backed pricing system.

- **Requirement:** Add `wholesale_price` to the `ProductModel` or create a new `Price` model.
- **Requirement:** Implement `GET /api/pricing` and `PATCH /api/pricing/{sku}`.
- **Business Rule:** Prices must be adjustable via CLI and reflect in the Catalog.

## 3. Finished Goods Inventory

Currently, the Manufacturer only tracks raw materials.

- **Requirement:** Update `Inventory` model to support `unit_type == "finished"`.
- **Requirement:** When a `ManufacturingOrder` is `completed`, the units should be added to the finished goods inventory.
- **Requirement:** Retailer orders should ideally be fulfilled from existing finished stock if available, or trigger production if not.

## 4. Order Lifecycle Updates

To support the "Purchasing" flow:
1. **Production:** Order status remains `released` while in production.
2. **Fulfillment:** Once `completed`, the order status should transition to `shipped` or `delivered` to allow the Retailer to "receive" the stock.
3. **Tracking:** Add `delivery_day` to the order model to simulate transit time.

## 5. Decision Framework (skills.md)

The Manufacturer decision logic needs to be updated to:
- Check finished goods stock before releasing new production.
- Raise/lower wholesale prices based on retailer demand vs. production capacity.
- Prioritize retailer orders based on age or urgency.
