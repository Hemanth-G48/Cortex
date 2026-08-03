import { useReducer, useCallback } from 'react';

/* ── Types ── */

interface PomodoroSettings {
  focusMinutes: number;
  breakMinutes: number;
  longBreakMinutes: number;
  sessionsBeforeLongBreak: number;
}

interface PomodoroState {
  timer: number;
  running: boolean;
  mode: 'focus' | 'break' | 'long-break';
  sessionCount: number;
  settings: PomodoroSettings;
}

type PomodoroAction =
  | { type: 'START_FOCUS' }
  | { type: 'START_BREAK' }
  | { type: 'START_LONG_BREAK' }
  | { type: 'TICK' }
  | { type: 'STOP' }
  | { type: 'SET_SETTINGS'; settings: Partial<PomodoroSettings> };

/* ── Helpers ── */

const createInitial = (overrides?: Partial<PomodoroSettings>): PomodoroState => {
  const settings = { focusMinutes: 25, breakMinutes: 5, longBreakMinutes: 15, sessionsBeforeLongBreak: 4, ...overrides };
  return { timer: settings.focusMinutes * 60, running: false, mode: 'focus', sessionCount: 0, settings };
};

const reducer = (state: PomodoroState, action: PomodoroAction): PomodoroState => {
  switch (action.type) {
    case 'START_FOCUS':
      return { ...state, timer: state.settings.focusMinutes * 60, running: true, mode: 'focus' };
    case 'START_BREAK':
      return { ...state, timer: state.settings.breakMinutes * 60, running: true, mode: 'break' };
    case 'START_LONG_BREAK':
      return { ...state, timer: state.settings.longBreakMinutes * 60, running: true, mode: 'long-break' };
    case 'TICK':
      if (state.timer <= 1) return { ...state, timer: 0, running: false };
      return { ...state, timer: state.timer - 1 };
    case 'STOP':
      return { ...state, timer: state.settings.focusMinutes * 60, running: false, mode: 'focus' };
    case 'SET_SETTINGS':
      return { ...state, settings: { ...state.settings, ...action.settings } };
    default:
      return state;
  }
};

/* ── Hook ── */

export const usePomodoro = (initialSettings?: Partial<PomodoroSettings>) => {
  const [state, dispatch] = useReducer(reducer, initialSettings, createInitial);

  const startFocus = useCallback(() => dispatch({ type: 'START_FOCUS' }), []);
  const startBreak = useCallback(() => dispatch({ type: 'START_BREAK' }), []);
  const startLongBreak = useCallback(() => dispatch({ type: 'START_LONG_BREAK' }), []);
  const tick = useCallback(() => dispatch({ type: 'TICK' }), []);
  const stop = useCallback(() => dispatch({ type: 'STOP' }), []);
  const updateSettings = useCallback((s: Partial<PomodoroSettings>) => dispatch({ type: 'SET_SETTINGS', settings: s }), []);

  const progress = state.mode === 'focus'
    ? 1 - state.timer / (state.settings.focusMinutes * 60)
    : state.mode === 'long-break'
      ? 1 - state.timer / (state.settings.longBreakMinutes * 60)
      : 1 - state.timer / (state.settings.breakMinutes * 60);

  return {
    ...state,
    progress,
    startFocus,
    startBreak,
    startLongBreak,
    tick,
    stop,
    updateSettings,
  };
};
