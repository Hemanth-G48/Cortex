import { useRef, type ReactNode } from 'react';

interface HeatmapCarouselProps {
  children: ReactNode;
  /** aria-label for accessibility. */
  label?: string;
}

/**
 * Horizontally scrollable, snap-on-card carousel with prev/next arrows.
 * Used to slide between habit heatmap cards instead of stacking them vertically.
 */
export const HeatmapCarousel = ({ children, label = 'Habit heatmaps' }: HeatmapCarouselProps) => {
  const ref = useRef<HTMLDivElement>(null);

  const scrollByCard = (dir: 1 | -1) => {
    const el = ref.current;
    if (!el) return;
    const card = el.querySelector<HTMLElement>('.heatmap-carousel-item');
    const step = card ? card.offsetWidth + 16 : el.clientWidth * 0.8;
    el.scrollBy({ left: dir * step, behavior: 'smooth' });
  };

  return (
    <div className="heatmap-carousel-wrap">
      <button
        type="button"
        className="heatmap-carousel-arrow heatmap-carousel-prev"
        aria-label={`Previous ${label}`}
        onClick={() => scrollByCard(-1)}
      >
        ‹
      </button>
      <div className="heatmap-carousel" ref={ref} role="region" aria-label={label}>
        {children}
      </div>
      <button
        type="button"
        className="heatmap-carousel-arrow heatmap-carousel-next"
        aria-label={`Next ${label}`}
        onClick={() => scrollByCard(1)}
      >
        ›
      </button>
    </div>
  );
};
