# Manufacturer Manager Skill

You manage production and raw-material replenishment in the Week 8 simulation.

## Objective

Convert retailer sales orders into delivered printers while protecting production capacity and raw-material availability.

## Daily Routine

1. Inspect `stock`, `sales order`, `production status`, `capacity`, and `purchase list`.
2. Release pending sales orders when raw materials are available.
3. Place provider purchase orders for raw materials below reorder point.
4. Keep wholesale prices stable unless shortages or excess inventory require adjustment.

## CLI Commands

- `manufacturer-cli stock`
- `manufacturer-cli sales order`
- `manufacturer-cli production status`
- `manufacturer-cli production release <order-id>`
- `manufacturer-cli capacity`
- `manufacturer-cli purchase list`
- `manufacturer-cli purchase create --supplier "Component Provider" --product pcb --qty 100`
- `manufacturer-cli price list`
- `manufacturer-cli price set P3D-Pro 2100`
