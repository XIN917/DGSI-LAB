# Final Deliverables & Delivery Plan

This document tracks the tasks required for the final submission of the DGSI Week 8 project, separating "doing the work" from "delivering the results."

## Part 5: Final Report (PDF)
*Target: 5–8 pages, generated via pandoc.*

- [ ] **Section A: System Architecture**
    - [ ] Full system diagram (mermaid/image).
    - [ ] ER diagrams for Provider, Manufacturer, and Retailer.
    - [ ] Turn engine sequence of operations.
    - [ ] Data flow description for market signals.
- [ ] **Section B: Agent Design**
    - [ ] Summaries of the 3 skill files.
    - [ ] Technical decisions made during skill authoring.
    - [ ] Reflections on agent strengths and weaknesses.
- [ ] **Section C: Simulation Results**
    - [ ] Embed 4 charts for `calm-market`.
    - [ ] Embed 4 charts for `holiday-rush`.
    - [ ] Written causal-chain interpretation (2–4 sentences per chart).
    - [ ] Answers to the 4 mandatory interpretation questions (Stock building, Stockout causes, Price oscillation, Bullwhip effect).
    - [ ] Scenario comparison paragraph.
- [ ] **Section D: Vibe-Coding Reflection**
    - [ ] Usage of Gemini CLI/Claude Code across 3 weeks.
    - [ ] Evaluation of what worked/failed.
    - [ ] Redesign reflection.

## Part 6: Presentation & Demo
*Target: Max 10 slides + 3-day live demo.*

- [ ] **Slide Deck (10 slides)**
    - [ ] System Overview (Arch diagram).
    - [ ] Agent Design (1 slide per role).
    - [ ] Results: "The Most Interesting Chart".
    - [ ] Reflection: Lessons learned.
- [ ] **Live Demo Rehearsal**
    - [ ] Choose a 3-day window for demo.
    - [ ] Narrate agent logic in real-time.
    - [ ] Prepare fallback plan for agent stalling.

## Part 7: Repository Final Polish
- [ ] Final `CLAUDE.md` and `README.md` review.
- [ ] Final `.gitignore` check (ensure no `.db` or `logs/` are tracked).
- [ ] Clean commit history with issue references.
- [ ] Ensure seed data is easily accessible and scripts work on a fresh clone.
