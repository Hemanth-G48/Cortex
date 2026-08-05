import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toggleAIChat } from '../utils/aiChatBus';

// Navigation shortcuts: press `g` then a letter (within 600ms) to jump.
export const SHORTCUTS: { key: string; label: string; path: string }[] = [
  { key: 'gh', label: 'Go to Dashboard', path: '/' },
  { key: 'ga', label: 'Go to Assignments', path: '/assignments' },
  { key: 'gt', label: 'Go to Tasks', path: '/tasks' },
  { key: 'gs', label: 'Go to Schedule', path: '/schedule' },
  { key: 'gx', label: 'Go to Exams', path: '/exams' },
  { key: 'gg', label: 'Go to Grades', path: '/grades' },
  { key: 'gd', label: 'Go to Flashcards', path: '/flashcards' },
  { key: 'gp', label: 'Go to Study Plans', path: '/study-plans' },
  { key: 'gq', label: 'Go to AI Quiz', path: '/quiz' },
  { key: 'gi', label: 'Import Syllabus', path: '/import' },
  { key: 'gn', label: 'Go to Notes', path: '/notes' },
  { key: 'gb', label: 'Go to Habits', path: '/habits' },
  { key: 'gr', label: 'Go to Analytics', path: '/analytics' },
  { key: 'gv', label: 'Go to Vault', path: '/vault' },
];

export const GLOBAL_SHORTCUTS = [
  { key: 'Ctrl+K', label: 'Open AI Chat' },
  { key: 'Ctrl+Shift+A', label: 'Quick add assignment' },
  { key: '?', label: 'Show this help' },
];

interface Options {
  onShortcutHelp?: () => void;
  onQuickCapture?: () => void;
}

export const useKeyboardShortcuts = ({ onShortcutHelp, onQuickCapture }: Options = {}) => {
  const navigate = useNavigate();
  const sequenceRef = useRef('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cbRef = useRef({ onShortcutHelp, onQuickCapture });
  cbRef.current = { onShortcutHelp, onQuickCapture };

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;

      // Ctrl/Cmd-based globals
      if (e.ctrlKey || e.metaKey) {
        if (e.key.toLowerCase() === 'k') {
          e.preventDefault();
          toggleAIChat();
          return;
        }
        if (e.shiftKey && e.key.toLowerCase() === 'a') {
          e.preventDefault();
          cbRef.current.onQuickCapture?.();
          return;
        }
        return;
      }

      // `?` opens the shortcut help (shift+/)
      if (e.key === '?' && !e.shiftKey) {
        e.preventDefault();
        cbRef.current.onShortcutHelp?.();
        return;
      }

      const key = e.key.toLowerCase();
      if (!/^[a-z]$/.test(key)) return;

      sequenceRef.current += key;
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        sequenceRef.current = '';
      }, 600);

      const match = SHORTCUTS.find((s) => s.key === sequenceRef.current);
      if (match) {
        sequenceRef.current = '';
        if (timerRef.current) clearTimeout(timerRef.current);
        navigate(match.path);
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('keydown', handleKey);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [navigate]);
};
