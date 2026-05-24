# 3D Printer Production Simulator — Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Finalize and verify all REST API endpoints, ensuring full wiring between the core simulation logic and the API layer.

---

## Task 1: Complete `PurchaseOrder` Creation logic

**Files:**
- Modify: `app/api/endpoints/purchase_orders.py`

- [ ] **Step 1: Finish the `create_purchase_order` endpoint**
  - Ensure `unit_cost`, `order_date`, `expected_delivery`, and `status` are correctly set.
  - Create the `PurchaseOrder` object and save to DB.
  - Ensure the `EventLog` entry is correctly created.

---

## Task 2: Complete Import/Export wiring

**Files:**
- Modify: `app/api/endpoints/import_export.py`
- Create/Verify: `app/utils/json_export.py`

- [ ] **Step 1: Finish `import_state` endpoint in `import_export.py`**
  - Complete the error handling and success response.
- [ ] **Step 2: Verify `app/utils/json_export.py` existence and basic logic**
  - If missing or incomplete, implement `export_full_state` and `import_full_state`.

---

## Task 3: API Verification & Integration Tests

**Files:**
- Create: `tests/test_api/test_integration.py`

- [ ] **Step 1: Write an integration test that covers the full flow via API**
  - Login to get token.
  - Create a Manufacturing Order.
  - Release the Order (check failure if materials missing).
  - Create a Purchase Order for missing materials.
  - Advance Day (check PO delivery).
  - Release the Order again (check success).
  - Advance Day until order completion.
  - Export state and Verify.
