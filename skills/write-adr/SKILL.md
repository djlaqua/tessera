---
name: write-adr
description: Record an architectural decision in docs/07-decision-log.md. Use whenever a design, dependency, or standard changes.
---

# Write an ADR

1. Open `docs/07-decision-log.md`; take the next ADR number.
2. Append, never edit past entries (supersede with a new ADR instead).
3. Fields: Date, Status (Proposed, Accepted, Superseded by ADR-N), Context, Decision, Consequences.
4. State at least one rejected alternative inside Context.
5. Update `docs/00-handoff-context.md` decisions table if the decision is Accepted.
6. Keep it under 150 words. No em dashes.
