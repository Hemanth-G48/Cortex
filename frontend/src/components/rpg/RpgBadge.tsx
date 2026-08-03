import type { ReactNode } from 'react';

type BadgeVariant = 'orange' | 'green' | 'red' | 'gold';

interface RpgBadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
  style?: React.CSSProperties;
}

const variantClass: Record<BadgeVariant, string> = {
  orange: 'rpg-badge-orange',
  green: 'rpg-badge-green',
  red: 'rpg-badge-red',
  gold: 'rpg-badge-gold',
};

export const RpgBadge = ({ children, variant = 'orange', className = '', style }: RpgBadgeProps) => {
  return (
    <span className={`rpg-badge ${variantClass[variant]} ${className}`} style={style}>
      {children}
    </span>
  );
};
