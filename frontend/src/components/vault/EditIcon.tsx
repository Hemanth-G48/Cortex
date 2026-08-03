interface EditIconProps {
  onClick: () => void;
  title?: string;
}

/** Small pencil button (spec UX improvement #4). */
export const EditIcon = ({ onClick, title = 'Edit' }: EditIconProps) => (
  <button
    aria-label={title}
    title={title}
    onClick={onClick}
    style={{
      background: 'none',
      border: '1px solid var(--vault-border)',
      borderRadius: 6,
      color: 'var(--vault-text-muted)',
      cursor: 'pointer',
      fontSize: 13,
      lineHeight: 1,
      padding: '4px 6px',
      flexShrink: 0,
    }}
  >
    ✏️
  </button>
);
