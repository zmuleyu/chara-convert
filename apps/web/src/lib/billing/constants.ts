// Minimum balance (in credits) at which the UI lets the user attempt an AI
// request. 100 credits == $0.01, comfortably above the ~13-credit minimum
// low-class request and the ~90-credit hold for typical high-class requests,
// so the gate fails open before the server returns 402.
//
// Single source of truth shared by AiAssistPanel's button gate and
// LowCreditCTA's threshold — keep them in sync via this constant.
export const MIN_BALANCE_TO_TRY = 100;
