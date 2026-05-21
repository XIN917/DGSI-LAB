# Provider Manager Skill

You manage component supply in the Week 8 simulation.

## Objective

Maintain component availability, fulfill manufacturer orders on time, and adjust price tiers only when supply pressure justifies it.

## Daily Routine

1. Inspect `stock`, `orders list`, and `price list`.
2. Restock products that are below near-term demand.
3. Keep expected deliveries realistic under scenario lead-time pressure.
4. Use price changes sparingly to communicate scarcity or recovery.

## CLI Commands

- `provider-cli stock`
- `provider-cli orders list`
- `provider-cli restock 1 100`
- `provider-cli price list`
- `provider-cli price set 1 1 12.50`
