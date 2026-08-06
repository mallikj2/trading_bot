# Corporate-Action and Total-Return Contract

**Contract:** `PHASE02-CORPORATE-ACTION-TOTAL-RETURN-v0.1`  
**Strategy:** `CSMOM-LS-v0.2`  
**Status:** Implemented; provider coverage evidence pending

## 1. Required separation

The normalized research dataset must expose distinct values:

| Field | Meaning | Permitted use |
|---|---|---|
| `raw_close` | Unadjusted price that could have traded | Execution, marking, raw dollar volume |
| `price_eligibility_close` | Current-session as-of split-adjusted close; equal to current raw close under the anchored convention | USD 10 universe threshold |
| `split_adjusted_close` | Back-adjusted close using only visible splits and stock multipliers | Reconciliation and audits |
| `total_return_adjusted_close` | Back-adjusted close using visible share multipliers and distributions | Reconciliation and audits |
| `adjusted_close` | Forward total-return index supplied to Phase 01 | Returns, momentum, volatility, SMA, correlation, benchmark |

A single provider-adjusted field may not be reused for all five roles unless its exact point-in-time semantics prove that the roles are equivalent.

## 2. Event-time economic equation

For a continuing action effective on session `t`, per old parent share:

```text
EventValue[t] = RawClose[t] × ShareMultiplier[t]
                + CashDistribution[t]
                + NonCashDistributionValue[t]
```

The gross total return is:

```text
GrossReturn[t] = EventValue[t] / RawClose[t-1]
```

The backward factors applied only to observations before `t` are:

```text
SplitFactor[t]       = 1 / ShareMultiplier[t]
TotalReturnFactor[t] = RawClose[t] / EventValue[t]
```

This produces the same adjacent-period return from the back-adjusted series and the forward total-return index.

## 3. Supported continuing actions

### Splits and reverse splits

```text
ShareMultiplier = new_shares / old_shares
```

Raw price and raw volume remain unchanged in storage. Position quantity is multiplied by the share multiplier.

### Cash dividends

The cash amount is per old parent share and must be expressed in the reporting currency. Long positions receive the distribution; short positions incur an equal signed liability.

### Stock dividends

```text
ShareMultiplier = 1 + stock_ratio
```

`stock_ratio` is incremental new parent shares per old parent share.

### Spinoffs

The action requires:

- child `instrument_id`;
- child shares distributed per old parent share;
- a point-in-time noncash valuation per old parent share;
- valuation timestamp, availability timestamp, method, currency, and raw lineage.

The total-return series uses the noncash value. Position processing creates a signed child position. A short parent therefore creates a short child obligation.

## 4. Supported terminal actions

Terminal types are merger, acquisition, delisting, liquidation, and bankruptcy.

```text
TerminalValue = CashConsideration + NonCashConsiderationValue
TerminalGrossReturn = TerminalValue / LastParentRawClose
```

The terminal observation is appended after the last parent trading bar, and the parent series stops. A same-session parent bar and terminal effective event are considered ambiguous and block processing.

An explicit zero-recovery observation is allowed. Missing consideration is not interpreted as zero.

## 5. Revisions and cancellation

For each `action_id`, select the latest record satisfying:

```text
available_at <= decision_at
```

Order by `(available_at, revision)`. Conflicting records sharing the latest key block the build.

A cancellation removes the action only for decisions at or after the cancellation became available. It does not rewrite an earlier frozen decision or dataset version.

## 6. Coverage contract

Every build requires an explicit coverage record containing:

- instrument ID;
- action types covered;
- covered-through timestamp;
- availability timestamp;
- completeness flag;
- source snapshot and revision.

The record must be available by the decision timestamp, marked complete, cover all required material action types, and extend through the decision timestamp. An empty action list without coverage is not evidence that no action occurred.

## 7. Valuation contract

A noncash valuation contains:

- action ID and parent instrument ID;
- purpose: distribution or terminal consideration;
- value per old parent share;
- valuation and availability timestamps;
- reporting currency;
- valuation method;
- component security where applicable;
- immutable source lineage and revision.

No FX conversion is implemented in this phase. Currency mismatch fails closed.

## 8. Unsupported or ambiguous events

The initial engine blocks:

- tender offers;
- rights distributions;
- mixed continuing and terminal actions on one session;
- multiple terminal actions on one session;
- continuing events without an ex-date bar;
- economic events on the first selected bar without a prior bar;
- terminal events that do not follow the last parent trading bar;
- spinoffs or stock consideration without point-in-time valuation.

## 9. Position effects

Position transformations use signed quantities:

- split or stock dividend: transform parent quantity;
- cash dividend: signed cash flow;
- spinoff: signed child quantity;
- stock merger: signed successor quantity;
- terminal event: parent quantity becomes zero.

These effects support later marked-to-market, short-liability, reconciliation, and attribution work. They do not authorize live order generation.
