// Env shape — referenced by index.ts, credit.ts, scheduled handler.
export interface Env {
  RATE_LIMIT_KV: KVNamespace;
  CREDIT_DB: D1Database;
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
export interface CreditError {
  code: 'missing_user_id' | 'insufficient_credit' | 'hold_not_found' | 'hold_already_settled' | 'bad_request';
  message: string;
}
