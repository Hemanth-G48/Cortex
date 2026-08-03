import { useRef, useEffect } from 'react';

/** Apply fade-in animation to elements when they mount */
export const useFadeIn = <T extends HTMLElement>() => {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (el) {
      el.style.opacity = '0';
      requestAnimationFrame(() => {
        el.style.transition = 'opacity 0.3s ease';
        el.style.opacity = '1';
      });
    }
  }, []);

  return ref;
};
