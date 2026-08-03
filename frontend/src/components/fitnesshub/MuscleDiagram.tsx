import type { ReactElement } from 'react';

interface MuscleDiagramProps {
  /** Muscle group name — matched to a mannequin region. */
  muscle: string;
  className?: string;
}

/**
 * Simplified front-view mannequin SVG (Phase 89). Each supported muscle group
 * highlights a specific region with a neon drop-shadow; unknown groups fall
 * back to a neutral colored placeholder silhouette.
 */
export const MuscleDiagram = ({ muscle, className = 'fh-muscle-svg' }: MuscleDiagramProps) => {
  const key = muscle.toLowerCase().replace(/\s+/g, '');
  const highlight = `url(#glow-${key})`;
  const accent = 'currentColor';

  const regions: Record<string, ReactElement> = {
    chest: (
      <>
        <ellipse cx="40" cy="58" rx="9" ry="12" fill={accent} opacity="0.85" />
        <ellipse cx="80" cy="58" rx="9" ry="12" fill={accent} opacity="0.85" />
      </>
    ),
    abs: (
      <g>
        <rect x="48" y="72" width="8" height="7" rx="1.5" fill={accent} />
        <rect x="58" y="72" width="8" height="7" rx="1.5" fill={accent} />
        <rect x="48" y="81" width="8" height="7" rx="1.5" fill={accent} />
        <rect x="58" y="81" width="8" height="7" rx="1.5" fill={accent} />
      </g>
    ),
    shoulders: (
      <>
        <ellipse cx="27" cy="44" rx="6" ry="9" fill={accent} />
        <ellipse cx="93" cy="44" rx="6" ry="9" fill={accent} />
      </>
    ),
    back: (
      <g>
        <rect x="34" y="46" width="26" height="18" rx="4" fill={accent} opacity="0.75" />
        <rect x="60" y="46" width="26" height="18" rx="4" fill={accent} opacity="0.75" />
      </g>
    ),
    lowerback: (
      <rect x="44" y="66" width="32" height="10" rx="3" fill={accent} opacity="0.8" />
    ),
    biceps: (
      <>
        <rect x="12" y="52" width="9" height="16" rx="3" fill={accent} />
        <rect x="99" y="52" width="9" height="16" rx="3" fill={accent} />
      </>
    ),
    triceps: (
      <>
        <rect x="14" y="52" width="7" height="18" rx="3" fill={accent} opacity="0.85" />
        <rect x="99" y="52" width="7" height="18" rx="3" fill={accent} opacity="0.85" />
      </>
    ),
    forearms: (
      <>
        <rect x="12" y="70" width="8" height="14" rx="3" fill={accent} />
        <rect x="100" y="70" width="8" height="14" rx="3" fill={accent} />
      </>
    ),
    glutes: (
      <ellipse cx="60" cy="96" rx="22" ry="9" fill={accent} opacity="0.8" />
    ),
    quads: (
      <>
        <rect x="42" y="104" width="12" height="22" rx="4" fill={accent} />
        <rect x="66" y="104" width="12" height="22" rx="4" fill={accent} />
      </>
    ),
    hamstring: (
      <>
        <rect x="42" y="112" width="11" height="20" rx="4" fill={accent} opacity="0.85" />
        <rect x="67" y="112" width="11" height="20" rx="4" fill={accent} opacity="0.85" />
      </>
    ),
    calves: (
      <>
        <rect x="44" y="132" width="10" height="14" rx="4" fill={accent} />
        <rect x="66" y="132" width="10" height="14" rx="4" fill={accent} />
      </>
    ),
  };

  const body = regions[key] ?? (
    <circle cx="60" cy="80" r="20" fill={accent} opacity="0.5" />
  );

  return (
    <svg viewBox="0 0 120 160" className={className} aria-label={`${muscle} muscle diagram`} role="img">
      <defs>
        <filter id={`glow-${key}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Body outline */}
      <g fill="none" stroke="currentColor" strokeWidth="2" opacity="0.35">
        {/* head */}
        <circle cx="60" cy="16" r="9" />
        {/* neck + torso */}
        <path d="M54 26 L50 40 L36 44 L26 78 L22 96 L34 100 L40 88 L44 104 L46 128 L60 140 L74 128 L76 104 L80 88 L86 100 L98 96 L94 78 L84 44 L70 40 L66 26 Z" />
        {/* arms */}
        <path d="M26 78 L14 70 L12 92 L20 96" />
        <path d="M94 78 L106 70 L108 92 L100 96" />
        {/* legs */}
        <path d="M46 128 L42 156 M74 128 L78 156" />
      </g>

      <g filter={highlight} color={accent}>
        {body}
      </g>
    </svg>
  );
};
