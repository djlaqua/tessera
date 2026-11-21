# Discovery Kit

Goal: 5 calls in 2 weeks. Decide the first segment and whether integrity is the reason to buy.

## Who to call (in this order)
1. Drone service operators doing inspection or survey with mixed fleets.
2. Vessel operators or port operators in areas with known GNSS interference (VERIFY area list, R9).
3. Utility or rail asset teams that fly drones next to fixed sensors.
4. Emergency response drone units (English-speaking first).

## Opening (30 seconds)
"I am building a tool that shows a fleet's positions on one live map and flags positions
that should not be trusted, for example during GPS interference. I am not selling today.
I want to learn how you handle this now."

## Questions (listen 80 percent)
1. Tell me about the last time a position or track looked wrong. What happened next?
2. How do you find out today? Who notices, and how long does it take?
3. What did it cost: time, a lost asset, an incident report, a customer complaint?
4. Which systems hold your telemetry today? (ground station, TAK, AIS, vendor cloud, files)
5. When a link drops, what do you lose?
6. After an incident, how do you reconstruct what happened?
7. Who would approve spending on fixing this, and what budget line would it come from?
8. If a pilot gave you an integrity report on your last 20 flights or voyages, would you share the logs?

## Demo (5 minutes, only after the questions)
Run `docker compose -f docker-compose.demo.yml up -d` beforehand. Show the copter circuit,
then the GPS glitch turning the raw GPS track red while the fused track stays green.
Say clearly: heuristic score, not certified navigation integrity.

## Qualify (write after each call)
| Signal | Strong | Weak |
| :--- | :--- | :--- |
| Pain | Named recent incident with cost | "Could be useful" |
| Data access | Will share logs for a pilot | Needs months of approvals |
| Budget owner | Identified, has a budget line | Unknown |
| Urgency | Interference seen this year | Hypothetical |

## Kill or pivot criteria
- Fewer than 3 of 5 calls name a real incident: integrity is not the wedge; test the
  "one picture and replay" problem statement instead.
- Nobody will share logs: the pilot model fails; consider an on-premise-only offer.

## After 5 calls
Record results in `private/discovery-notes.md` (gitignored) and the decision in
`docs/07-decision-log.md`.
