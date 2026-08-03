import type { ReactNode, MouseEvent } from 'react';

type ButtonVariant = 'orange' | 'green' | 'ghost';
type ButtonSize = 'sm' | 'md';

interface RpgButtonProps {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void;
  icon?: string;
  className?: string;
  type?: 'button' | 'submit';
}

const variantClass: Record<ButtonVariant, string> = {
  orange: 'rpg-btn-orange',
  green: 'rpg-btn-green',
  ghost: 'rpg-btn-ghost',
};

const sizeStyle: Record<ButtonSize, React.CSSProperties> = {
  sm: { padding: '4px 10px', fontSize: '0.7rem' },
  md: {},
};

export const RpgButton = ({
  children,
  variant = 'orange',
  size = 'md',
  disabled = false,
  onClick,
  icon,
  className = '',
  type = 'button',
}: RpgButtonProps) => {
  return (
    <button
      className={`rpg-btn pixel-btn-press ${variantClass[variant]} ${size === 'sm' ? 'rpg-btn-sm' : ''} ${className}`}
      type={type}
      disabled={disabled}
      onClick={onClick}
      style={{
        ...sizeStyle[size],
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      {icon && <span style={{ fontSize: size === 'sm' ? '0.8rem' : '1rem' }}>{icon}</span>}
      {children}
    </button>
  );
};
