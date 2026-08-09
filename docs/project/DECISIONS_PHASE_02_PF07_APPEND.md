# Decision Log Append — P02-PF07

## D02-PF07-01 — Runtime time comes only from a controlled session clock

Accepted. Synthetic decisions/actions are driven by explicit plan timestamps. Host wall-clock speed cannot affect results.

## D02-PF07-02 — Simulation plans and commands are content addressed

Accepted. Editing command order, timestamp, kind, or payload changes deterministic command/plan IDs and therefore the evidence lineage.

## D02-PF07-03 — A session cannot complete with nonterminal orders

Accepted. `SESSION_COMPLETED` requires all commands applied and all OMS orders terminal.

## D02-PF07-04 — Restart equivalence is quiescent-only in PF07

Accepted. A restart may continue only when prior orders are terminal. Open/unknown-order crash recovery and broker-truth reconciliation are explicitly deferred to PF10.

## D02-PF07-05 — PF04 runtime safety is enforced inside simulation

Accepted. Synthetic protection evidence flows through PF04. Recovery to a less restrictive state requires explicit approval; the runtime cannot bypass REDUCING/HALTED permissions.

## D02-PF07-06 — PF07 is not deployed paper trading

Accepted. SimulatedBroker remains local/network-free; no external broker account, live endpoint, or market-data credential is used.
