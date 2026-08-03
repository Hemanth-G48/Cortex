import { createContext } from 'react';

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

interface ToastCtx {
  toasts: Toast[];
  toast: (message: string, type?: Toast['type']) => void;
  dismiss: (id: number) => void;
}

export const ToastContext = createContext<ToastCtx>({ toasts: [], toast: () => {}, dismiss: () => {} });
export type { Toast, ToastCtx };
