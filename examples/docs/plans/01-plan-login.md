# Plan 01: login

An example plan. Its tasks can be cited as `01/1.1`, `01/2.3`…

## Decisions

| # | Decision | Status |
|---|---|---|
| L1 | Accounts lock after repeated failures instead of showing a captcha | ✅ |

## Epic 1 — Sign in

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 1.1 | Email and password form | A registered user signs in and lands on the dashboard; a wrong password shows one generic error | ✅ |
| 1.2 | Remember me | With the box checked, the session survives closing the browser for 30 days; without it, it doesn't | 🟡 |

## Epic 2 — Protection

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 2.1 | Count failed attempts | Each failure is recorded with time and IP | ⬜ |
| 2.3 | Lock after failed attempts | After 5 failures in 15 min the account locks for 15 min (L1); tested | ⬜ |
| 2.3b | Unlock by email | The locked user gets a one-time link that unlocks the account | ⬜ |
