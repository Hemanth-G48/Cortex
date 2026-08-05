// Shared AI-chat toggle bus so keyboard shortcuts / layout can open the panel.
// Kept in its own module (not co-located with the component) so fast-refresh
// lint rules stay satisfied.

type Listener = () => void;
const listeners = new Set<Listener>();

export const onAIChatToggle = (fn: Listener) => {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
};

export const toggleAIChat = () => {
  listeners.forEach((l) => l());
};
