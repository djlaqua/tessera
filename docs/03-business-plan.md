# Business Plan (lean)

## Customers (test order)
1. Civil drone operators (inspection, survey) with mixed fleets.
2. Utilities, rail, and port operators with drones plus fixed sensors.
3. Emergency services and disaster response units.
4. Defense primes and drone makers as integration partners and later acquirers (Phase 2, after clearance-free proof).

## Problem statements to validate
1. "We cannot tell whether a position we saw was real, during or after an incident."
2. "We have drones and sensors but no single live picture, we lose data on weak links, and we cannot replay incidents."

## Offer
- **Pilot (8 weeks):** install edge and hub on the customer's data, replay their past incidents,
  deliver an integrity report per flight or voyage, then run live for the rest of the pilot.
- **Edge daemon:** adapters, normalization, log, replay (licensing per ADR-012).
- **Paid:** hub with live map, integrity scoring and alerts, multi-site sync, retention and
  audit export, SSO, support.

## Demo asset (ready)
`docker compose -f docker-compose.demo.yml up --build -d` runs a simulated copter that flies a
circuit, injects a GPS glitch, syncs signed data to the hub and shows the glitch flagged on
the live map. Use it in every discovery call (`docs/09-discovery-kit.md`).

## Pricing hypotheses (VERIFY via discovery)
| Tier | Price | Buyer |
| :--- | :--- | :--- |
| Pilot | 2k to 5k EUR fixed, 8 weeks | Operator with one concrete bottleneck |
| Team | 300 to 1,000 EUR per month per site | Operators, utilities |
| Enterprise | Custom annual | Ports, grids, agencies |

## Go to market
- English first, private and international buyers. German public sector later via a German-speaking partner.
- Channels: TAK and drone communities, MAVLink forums, DLR and Munich cluster intros, EU/NATO accelerators.
- Proof assets: public demo with recorded flight replay, open adapter library, one written case study.

## Costs (phase 1)
Laptop, small cloud VM, domain, one Raspberry Pi or Jetson for edge tests: under 500 EUR.
Phase 2 adds Jetson Orin, test drone, sensors: 2k to 15k EUR (funded by pilots or grants).

## Funding paths (VERIFY eligibility)
Pilot revenue first. Then EXIST, ZIM, Bavarian grants, NATO DIANA, EU programs, pre-seed VC.

## Milestones
| Month | Milestone | Exit signal |
| :--- | :--- | :--- |
| 1 | Engine, sync, map, integrity v0, demo (done) and 5 discovery calls | 3 calls confirm the pain |
| 3 | Public replay demo, 1 pilot LOI | Signed LOI or paid pilot |
| 6 | First paid pilot delivered, integrity prototype on replay data | Pilot renewal intent |
| 9 | 3 paying sites or 1 grant | Repeatable sales motion |

## Risks and mitigations
- Crowded middleware space: stay on a narrow wedge, win on resilience and replay.
- Solo bandwidth: strict scope, open-source adapters from the community.
- Export and legal exposure: see `06-founder-constraints-and-compliance.md`.
- Language barrier for public sector: partner later.
- Overclaiming integrity: the score is a heuristic, not a certified navigation integrity
  monitor. Say so in every demo and contract (ADR-011).
- Public repository: strategy and code are visible to competitors, and export rules may
  apply to Phase 2 code (ADR-012).
