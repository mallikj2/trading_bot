import test from 'node:test';
import assert from 'node:assert/strict';
import { filterDirection, numericScore, rankLeads, statusClass, watchlistHeadline } from '../src/lib/selectors.js';
import type { TradeLeadView, WatchlistView } from '../src/lib/models.js';

function lead(symbol: string, direction: 'LONG'|'SHORT', score: string): TradeLeadView {
  return { lead_id:symbol, symbol, decision_symbol:symbol, direction, score, state:'QUALIFIED', trend_state:'ABOVE_SMA200', volatility_state:'WITHIN_LIMIT', earnings_state:'CLEAR', cost_state:'CLEAR', borrow_state: direction === 'LONG' ? 'NOT_APPLICABLE' : 'AVAILABLE', estimated_spread_bps:'10', estimated_cost_bps:'12', proposed_weight:null, proposed_shares:null, decision_at:'2026-08-08T20:30:00+00:00', valid_until:'2026-08-15T20:30:00+00:00', strategy_id:'CSMOM-LS', strategy_version:'0.2', reasons:[], immutable_hash:'a', content_hash:'b' };
}

test('rankLeads sorts by absolute score', () => { assert.deepEqual(rankLeads([lead('A','LONG','0.8'),lead('B','SHORT','-1.2')]).map(x=>x.symbol), ['B','A']); });
test('filterDirection keeps requested side', () => { assert.deepEqual(filterDirection([lead('A','LONG','1'),lead('B','SHORT','-1')], 'SHORT').map(x=>x.symbol), ['B']); });
test('numericScore fails closed to zero for bad display input', () => { assert.equal(numericScore('nope'), 0); });
test('statusClass distinguishes pass and block', () => { assert.equal(statusClass('PASS'), 'good'); assert.equal(statusClass('BLOCKED'), 'bad'); });
test('watchlist headline uses deterministic blocker detail', () => { const w: WatchlistView = { lead_id:'1',symbol:'A',direction:'LONG',state:'WATCHLIST',score:'0.6',blocking_reasons:[{code:'X',detail:'Need higher score',available_at:'x',blocking:true}],qualification_actions:['Wait'],valid_until:'x' }; assert.equal(watchlistHeadline(w), 'Need higher score'); });
