-- 0001_credit_ledger.sql
-- Schema for credit ledger. Owner: docs/specs/2026-05-29-or-credit-router-design.md
-- Invariant 1: sum(credit_ledger.delta) per user == credit_balance.balance + credit_balance.held
-- Invariant 2: every credit_hold row settles to 'debited' or 'refunded'
-- Invariant 3: credit_balance.balance + credit_balance.held >= 0 always

CREATE TABLE credit_balance (
  user_id    TEXT PRIMARY KEY,
  balance    INTEGER NOT NULL DEFAULT 0,
  held       INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);

CREATE TABLE credit_hold (
  hold_id    TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL,
  amount     INTEGER NOT NULL,
  status     TEXT NOT NULL CHECK (status IN ('open', 'debited', 'refunded')),
  created_at INTEGER NOT NULL,
  settled_at INTEGER
);
CREATE INDEX idx_credit_hold_open ON credit_hold(status, created_at) WHERE status='open';

CREATE TABLE credit_ledger (
  ts         INTEGER NOT NULL,
  user_id    TEXT NOT NULL,
  delta      INTEGER NOT NULL,
  reason     TEXT NOT NULL CHECK (reason IN ('hold','debit','refund','topup','grant')),
  hold_id    TEXT,
  note       TEXT
);
CREATE INDEX idx_credit_ledger_user_ts ON credit_ledger(user_id, ts);
