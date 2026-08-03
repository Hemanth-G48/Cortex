import type { CSSProperties } from 'react';

/* ── Skeleton helpers ── */

interface SkeletonBoxProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  style?: CSSProperties;
}

export const SkeletonBox = ({ width = '100%', height = 16, borderRadius = 'var(--radius)', style }: SkeletonBoxProps) => (
  <div
    className="skeleton"
    style={{ width, height, borderRadius, ...style }}
  />
);

export const SkeletonCard = () => (
  <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
    <SkeletonBox height={16} width="60%" />
    <SkeletonBox height={12} width="80%" />
    <SkeletonBox height={12} width="40%" />
  </div>
);

export const SkeletonTable = (rows = 3) => (
  <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
    <SkeletonBox height={12} width="100%" />
    {Array.from({ length: rows }).map((_, i) => (
      <SkeletonBox key={i} height={10} width={`${85 - i * 10}%`} />
    ))}
  </div>
);

export const SkeletonStatTile = () => (
  <div className="stat-tile" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
    <SkeletonBox height={10} width="50%" />
    <SkeletonBox height={28} width="30%" />
  </div>
);
