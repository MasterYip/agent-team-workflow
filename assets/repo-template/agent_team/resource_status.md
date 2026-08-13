# Resource And External Job Status

Last refreshed: {{CONFIRMED_AT}}

## Reservations

| Reservation ID | Task | Resource | Owner | State | Start / expiry | Process/job ID | Last verified | Output path | Release condition |
|---|---|---|---|---|---|---|---|---|---|
| none | none | none | manager | released | N/A | none | {{CONFIRMED_AT}} | none | already released |

Allowed reservation states: `planned`, `reserved`, `active`, `released`, `failed`.

Do not infer release from a stale heartbeat. Verify the scheduler, process, terminal marker, and artifacts read-only before changing state or authorizing reuse.
