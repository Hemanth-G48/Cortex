import { useEffect } from 'react';

interface PDFReaderProps {
  url: string;
  title: string;
  onClose: () => void;
}

export const PDFReader = ({ url, title, onClose }: PDFReaderProps) => {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000 }}>
      <div className="modal" style={{ width: '95vw', maxWidth: '1200px', height: '90vh', display: 'flex', flexDirection: 'column' }} onClick={(e: React.MouseEvent) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>{title}</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>✕ Close</button>
        </div>
        <iframe src={url} title={title} className="pdf-frame" style={{ flex: 1, border: 'none', width: '100%' }} />
      </div>
    </div>
  );
};