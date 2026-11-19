# Business Plan (lean)

## Customers (test order)
1. Civil drone operators (inspection, survey) with mixed fleets.
2. Utilities, rail, and port operators with drones plus fixed sensors.
3. Emergency services and disaster response units.
4. Defense primes and drone makers as integration partners and later acquirers (Phase 2, after clearance-free proof).

## Problem statement to validate
"We have sensors and drones but cannot see one live picture, lose data on weak links, and cannot replay incidents."

## Offer
- **Edge daemon** (free or open core): adapters, normalization, log, replay.
- **Paid**: multi-site sync, fleet dashboard, retention and audit export, SSO, support, integrity module.

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
| 1 | Sprint 01 scaffold, 5 discovery calls | 3 calls confirm the pain |
| 3 | Public replay demo, 1 pilot LOI | Signed LOI or paid pilot |
| 6 | First paid pilot delivered, integrity prototype on replay data | Pilot renewal intent |
| 9 | 3 paying sites or 1 grant | Repeatable sales motion |

## Risks and mitigations
- Crowded middleware space: stay on a narrow wedge, win on resilience and replay.
- Solo bandwidth: strict scope, open-source adapters from the community.
- Export and legal exposure: see `06-founder-constraints-and-compliance.md`.
- Language barrier for public sector: partner later.
