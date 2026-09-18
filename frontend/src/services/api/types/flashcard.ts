// Flashcards + leaderboard types.
// Extracted from services/api.ts (F8 split).

// ----- Flashcards types (99-phase plan, Groups 4-5) -----
export interface Flashcard {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  difficulty: string;
  streak: number;
  next_review: string | null;
  created_at: string | null;
}

// FSRS spaced-repetition state (Idea 52 — vendored py-fsrs).
export interface FlashcardSchedule {
  card_id: number;
  next_review: string | null;
  interval_days: number;
  state: number | null;
  stability: number | null;
  fsrs_difficulty: number | null;
  reps: number;
  lapses: number;
  streak: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  name: string;
  username: string | null;
  avatar_class: string | null;
  level: number;
  current_streak: number;
  total_xp: number;
  me: boolean;
}

export interface LeaderboardMe {
  user_id: number;
  total_xp: number;
  rank: number;
  percentile: number;
  total_users: number;
}

export interface LeaderboardResponse {
  items: LeaderboardEntry[];
  me: LeaderboardMe;
}

export interface DueFlashcard {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  difficulty: string;
  next_review: string | null;
  interval_days: number;
  streak: number;
}

export interface FlashcardDeck {
  id: number;
  name: string;
  course_id: number | null;
  created_at: string | null;
  card_count: number;
  cards: Flashcard[];
}
