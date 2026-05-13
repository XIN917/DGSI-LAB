# Issue #30: JSON import with validation

## Description
Implement full game state import from JSON with schema validation.

## Tasks
- [x] Create import function for full state
- [x] Validate JSON schema before importing
- [x] Handle version compatibility
- [x] Transaction-based import (rollback on error)
- [x] API endpoint /api/import/full-state
- [x] Upload button in dashboard

## Acceptance Criteria
- Invalid JSON rejected with clear error
- All state restored correctly
- No partial imports on failure

## Phase
Phase 5 - Import/Export & Polish
