# Issue #3: Authentication system (login, session, JWT)

## Description
Implement a complete authentication system for the simulator.

## Tasks
- [x] Create password hashing utilities (bcrypt)
- [x] Create JWT token generation and validation
- [x] Implement login endpoint with rate limiting
- [x] Implement logout endpoint
- [x] Implement current user endpoint
- [x] Create auth dependency for protected routes
- [x] Seed default admin user on first run

## Acceptance Criteria
- Users can login with username/password
- Sessions expire after 24 hours
- Protected routes require valid token
- Default admin user created on first run

## Phase
Phase 1 - Foundation
