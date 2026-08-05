import type { Book } from '../../services/api';

interface BookCardProps {
  book: Book;
  onFinish?: (id: number) => void;
  onStart?: (id: number) => void;
  onRemove?: (id: number) => void;
  onOpen?: (url: string) => void;
}

const categoryColors: Record<Book['category'], { bg: string; color: string }> = {
  reading: { bg: 'var(--info-muted)', color: 'var(--info)' },
  finished: { bg: 'var(--success-muted)', color: 'var(--success)' },
  want: { bg: 'var(--warning-muted)', color: 'var(--warning)' },
};

export const BookCard = ({ book, onFinish, onStart, onRemove, onOpen }: BookCardProps) => {
  const colors = categoryColors[book.category];
  const hasFile = book.file_url != null;

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', position: 'relative' }}>
      {book.cover_url && (
        <img
          src={book.cover_url}
          alt={book.title}
          style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 'var(--radius)', cursor: hasFile ? 'pointer' : 'default' }}
          onClick={() => hasFile && onOpen?.(book.file_url!)}
          role={hasFile ? 'button' : undefined}
          tabIndex={hasFile ? 0 : undefined}
          onKeyDown={(e) => { if (e.key === 'Enter' && hasFile) onOpen?.(book.file_url!); }}
        />
      )}
      <div style={{ fontWeight: 600, fontSize: '0.9rem', cursor: hasFile ? 'pointer' : 'default' }} onClick={() => hasFile && onOpen?.(book.file_url!)} role={hasFile ? 'button' : undefined} tabIndex={hasFile ? 0 : undefined} onKeyDown={(e) => { if (e.key === 'Enter' && hasFile) onOpen?.(book.file_url!); }}>
        {book.title}
      </div>
      {book.author && (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{book.author}</div>
      )}
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <span className="badge" style={{ background: colors.bg, color: colors.color }}>{book.category}</span>
        {hasFile && (
          <>
            {book.category === 'reading' && onStart && (
              <button type="button" className="btn btn-primary btn-sm" onClick={() => onStart(book.id)}>Read</button>
            )}
            {book.category === 'finished' && onFinish && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => onFinish(book.id)}>Re-read</button>
            )}
          </>
        )}
        {onRemove && (
          <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)', marginLeft: 'auto' }} aria-label={`Remove ${book.title}`} onClick={() => onRemove(book.id)}>✕</button>
        )}
      </div>
    </div>
  );
};