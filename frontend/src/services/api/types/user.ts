// User / profile domain types.
// Extracted from services/api.ts (F8 split).

export interface User {
  id: number;
  name: string;
  avatar?: string | null;
  avatar_class?: string;
  current_level: number;
  current_streak: number;
  total_xp: number;
  current_weight?: number | null;
  initial_weight?: number | null;
  target_weight?: number | null;
  membership_status?: string;
  next_payment_date?: string | null;
  username?: string | null;
  email?: string | null;
  role?: string;
  is_admin?: boolean;
  institution_id?: number | null;
  program_id?: number | null;
  created_at?: string | null;
}
