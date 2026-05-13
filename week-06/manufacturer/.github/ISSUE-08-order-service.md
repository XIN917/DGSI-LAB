# Issue #8: Order service

## Description
Implement manufacturing order service for managing production orders.

## Tasks
- [x] Implement order creation
- [x] Calculate BOM requirements for an order
- [x] Check material availability against BOM
- [x] Release order to production (reserves materials)
- [x] Mark order as waiting_materials if insufficient
- [x] Process order completion within capacity limits
- [x] Cancel order (releases reservations)
- [x] Add API endpoints for all operations

## Acceptance Criteria
- Orders created with correct BOM breakdown
- Can release only if materials available
- Missing materials triggers waiting_materials state
- Daily capacity enforced

## Phase
Phase 2 - Core Simulation
