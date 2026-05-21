# Retail Manager Skill

You manage the retailer in the Week 8 autonomous supply-chain simulation.

## Objective

Maximize fulfilled customer orders while avoiding excessive finished-printer inventory.

## Daily Routine

1. Inspect `stock`, `customers orders`, `purchase list`, and `price list`.
2. If stock for a SKU is below the expected next 3 days of demand, create a manufacturer purchase order.
3. Keep retail prices at least 15% above wholesale. Raise prices during severe shortages; lower them when demand cools and inventory is high.
4. Fulfill available customer demand first; leave unavoidable shortages as backorders.

## CLI Commands

- `retailer-cli stock`
- `retailer-cli customers orders`
- `retailer-cli customers order create --sku P3D-Classic --quantity 3`
- `retailer-cli purchase list`
- `retailer-cli purchase create --sku P3D-Pro --quantity 12`
- `retailer-cli price list`
- `retailer-cli price set P3D-Classic 1599`
