// Env shape — referenced by index.ts, credit.ts, scheduled handler, CreditDO.
export interface Env {
  RATE_LIMIT_KV: KVNamespace;
  CREDIT_DB: D1Database;
  CREDIT_DO: DurableObjectNamespace;
}

export interface BalanceView {
  balance: number;
  held: number;
}

export interface HoldRequest {
  amount: number;
}

export interface HoldResponse {
  holdId: string;
  newBalance: number;
}

export interface DebitRequest {
  holdId: string;
  actualAmount: number;
}

export interface DebitResponse {
  newBalance: number;
}

export interface RefundRequest {
  holdId: string;
}

export interface RefundResponse {
  newBalance: number;
}

// Error envelope used by every credit endpoint for non-2xx.
//
// Code semantics (load-bearing for credit_client.py retry policy):
//   - bad_request (400)         : malformed input — never retry
//   - missing_user_id (400)     : header missing — never retry
//   - insufficient_credit (402) : balance < amount — never retry
//   - not_found (404)           : unknown route or hold_id — never retry
//   - hold_not_found (404)      : debit on unknown hold — never retry
//   - hold_already_settled (409): hold debited/refunded — never retry (idempotency signal)
//   - service_unavailable (503) : DO unreachable / transient — retry idempotent ops
//   - internal_error (500)      : unexpected throw inside DO — retry idempotent ops
export interface CreditError {
  code:
    | 'missing_user_id'
    | 'insufficient_credit'
    | 'hold_not_found'
    | 'hold_already_settled'
    | 'bad_request'
    | 'not_found'
    | 'service_unavailable'
    | 'internal_error';
  message: string;
}
