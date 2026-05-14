### DGSI Week 6: The Supply Chain (Part 1) — Project Report

**Author:** David Morais, Zixin Zhang, Zhipeng Lin and Zhehan Xiang

**Date:** May 10, 2026  

**Subject:** Week 6 Challenge — Two Apps Talking

---

#### 1. Architecture: Distributed Simulation Wiring

The Week 6 architecture transitions the project from a monolithic application into a distributed system composed of two independent services: the **Manufacturer App** (extended from Week 5) and the newly built **Provider App**.

**Key Components:**

*   **Provider App (Port 8001):** Acts as a component supplier. It maintains its own database (`provider.db`), simulates its own time (day counter), and manages inventory and order fulfillment.

*   **Manufacturer App (Port 8002):** The factory floor simulator. It now includes a configuration layer to manage external providers and a service layer to poll the Provider's REST API for order updates.

*   **Communication:** All interaction between the two apps occurs via HTTP/REST. Neither app has direct access to the other’s database, ensuring strict isolation and a contract-based relationship.


---

#### 2. The REST Contract: Designing for Decoupling

The Provider's API was designed to be the single source of truth for its catalog and order states. We implemented the following endpoints to serve as the "contract" between the services:

*   **`GET /api/catalog`**: Returns the list of products, lead times, and volume discount tiers. This allows the Manufacturer to dynamically fetch pricing without hardcoded values.
*   **`GET /api/stock`**: Provides current inventory levels. While the Manufacturer typically uses the catalog, this endpoint is crucial for transparency during debugging and CLI inspection.
*   **`POST /api/orders`**: The entry point for purchasing. It accepts a `product_id`, `quantity`, and `buyer` name. The Provider validates stock availability and calculates the `expected_delivery_day` based on current simulation time.
*   **`GET /api/orders/{id}`**: A critical polling endpoint. The Manufacturer uses this to check if an order has transitioned to `DELIVERED`.
*   **`POST /api/day/advance`**: Synchronizes simulated time. Advancing time on the Provider triggers the state machine logic that moves orders from `PENDING` → `CONFIRMED` → `SHIPPED` → `DELIVERED`.

**Rationale:** We chose a **polling pattern** (Manufacturer queries Provider) over a webhook/push notification system to minimize architectural complexity for this phase, ensuring that time advancement remains deterministic and human-driven.

---

#### 3. The Scenario: 5-Day Manual Integration

We executed the "Ironclad Rule" scenario to verify the end-to-end integration:

1.  **Day 0**: Initialized both apps. Provider started with 500 PCBs; Manufacturer with 5 PCBs.
2.  **Day 1**: Placed a purchase order for 50 PCBs via `manufacturer-cli purchase create`. The Provider logged the order as `PENDING` with an expected arrival on **Day 4**. Both apps were advanced one day.
3.  **Days 2–3**: Advanced both apps. The Provider's internal state machine moved the order to `CONFIRMED` and then `SHIPPED`. The Manufacturer's event log showed polling attempts with "pending" status.
4.  **Day 4**: Advanced the Provider first. The order status changed to `DELIVERED`. When the Manufacturer advanced, its polling logic detected the delivery, automatically updated its local inventory to **55 PCBs**, and marked the local PO as `delivered`.
5.  **Verification**: A second order for 10 PCBs was placed to ensure the process was repeatable and not a "one-off" success.

**Surprises**: The most significant learning was the importance of the "Advance Provider first" sequence on Day 4. If the Manufacturer advances before the Provider processes its daily deliveries, the Manufacturer "misses" the arrival for that cycle, effectively adding a 1-day delay. This highlighted the need for the turn engine planned for Week 7.

---

#### 4. Vibe-Coding Notes: Reflection on AI Assistance

Building this distributed system through "vibe-coding"—leveraging Gemini/AI for high-speed prototyping—provided several insights into the future of agentic software engineering:

*   **The Power of Static Anchors (What Went Well):** The AI was exceptional at boilerplate generation for FastAPI schemas, SQLAlchemy models, and Typer CLI commands. By using `prd.md` and `architecture.md` as "ground truth" anchors, the AI maintained high consistency across the separate Provider and Manufacturer codebases, drastically reducing the manual effort required for REST integration.
*   **The "Context Drift" Challenge (Where it Struggled):** While the AI excelled at structural code, it struggled with visual and semantic nuances. 
    *   **UI/UX Intuition:** It failed to solve accessibility issues like UI contrast, requiring manual human intervention.
    *   **Requirements Alignment:** Initial data modeling suggestions occasionally drifted from the specific business logic required for the 5-day scenario, necessitating iterative corrections.
    *   **Holistic Orchestration:** The AI initially prioritized the CLI-based interaction model; I had to explicitly guide it to bridge the gap between the backend services and the Dashboard UI.

---

#### 5. Conclusion

Week 6 successfully established the deterministic foundation of the supply chain. By isolating the Provider and Manufacturer into separate processes and enforcing communication via a strict REST contract, we have built a robust plumbing system. This "rock solid" foundation is now ready for the introduction of LLM-powered agents and an automated turn engine in the coming weeks.