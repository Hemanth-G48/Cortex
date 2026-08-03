interface ProgressRingProps {
  progress: number;   // 0..1
  size?: number;
  strokeWidth?: number;
  color?: string;
}

/** SVG circular progress ring for the pomodoro timer */
export const ProgressRing = ({ progress, size = 200, strokeWidth = 6, color = 'var(--accent)' }: ProgressRingProps) => {
  const r = (size - strokeWidth) / 2;
  const circum = 2 * Math.PI * r;
  const offset = circum - progress * circum;

  return (
    <svg width={size} height={size} className="progress-ring">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="var(--border)"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circum}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: 'stroke-dashoffset 0.5s ease' }}
      />
    </svg>
  );
};
