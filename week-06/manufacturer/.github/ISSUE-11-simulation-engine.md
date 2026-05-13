# Issue #11: Simulation engine (day advancement cycle)

## Description
Implement the core simulation engine that processes a full day cycle.

## Tasks
- [x] Create advance_day function
- [x] Sequence: Generate demand -> Process POs -> Process orders -> Log events
- [x] Enforce daily capacity limits
- [x] Handle partial PO deliveries
- [x] Update order statuses based on completion
- [x] Take daily inventory snapshot
- [x] Add API endpoint to trigger advance

## Acceptance Criteria
- Clicking "Advance Day" runs complete cycle
- All events happen in correct order
- Capacity limits enforced
- State consistent after each cycle

## Phase
Phase 2 - Core Simulation
