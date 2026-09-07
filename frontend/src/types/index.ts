export interface User {
  id: number;
  username: string;
  email: string;
  role: 'customer' | 'admin';
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface Policy {
  id: number;
  user: number;
  user_username?: string;
  policy_number: string;
  policy_type: 'auto' | 'health' | 'property';
  coverage_amount: string; // decimal as string
  premium: string;
  start_date: string; // YYYY-MM-DD
  status: 'pending_activation' | 'active' | 'expired' | 'cancelled';
  created_at: string;
}

export interface Claim {
  id: number;
  policy: number;
  policy_number?: string;
  submitted_by?: number;
  submitted_by_username?: string;
  claim_amount: string;
  description: string;
  date_filed: string;
  status: 'pending' | 'approved' | 'rejected';
  fraud_flag: boolean;
  fraud_reason?: string; // Only visible to admins
  reviewed_by?: number;
  reviewed_by_username?: string;
  reviewed_at?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
