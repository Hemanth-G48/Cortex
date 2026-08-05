import { useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { SkeletonCard } from '../components/shared/Skeleton';
import { BookTabs } from '../components/reading/BookTabs';
import { BookCard } from '../components/reading/BookCard';
import { ReadingInsights } from '../components/reading/ReadingInsights';
import { PDFReader } from '../components/reading/PDFReader';
import { useReading } from '../hooks/useReading';
import { bookApi } from '../services/api';

export const Reading = () => {
  const { books, insights, loading, refresh, addBook, removeBook } = useReading();
  const [tab, setTab] = useState<'all' | 'reading' | 'finished' | 'want'>('all');
  const [showAdd, setShowAdd] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState<'reading' | 'finished' | 'want'>('reading');
  const [uploading, setUploading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfTitle, setPdfTitle] = useState('');

  const handleAdd = async () => {
    if (!title.trim()) return;
    await addBook(title.trim(), author || null, category);
    setTitle('');
    setAuthor('');
    setCategory('reading');
    setShowAdd(false);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const { url } = await bookApi.uploadFile(file);
      const fname = file.name.replace(/\.pdf$/i, '');
      const created = await bookApi.create({ title: fname || 'Untitled', category: 'reading' });
      await bookApi.update(created.id, { file_url: url });
      setShowUpload(false);
      await refresh();
    } catch {
      /* silent */
    } finally {
      setUploading(false);
    }
    e.target.value = '';
  };

  const handleFinish = useCallback(async (id: number) => {
    await bookApi.update(id, { category: 'finished' });
    await refresh();
  }, [refresh]);

  const handleStart = useCallback(async (id: number) => {
    await bookApi.update(id, { category: 'reading' });
    await refresh();
  }, [refresh]);

  const handleRemove = useCallback(async (id: number) => {
    await removeBook(id);
  }, [removeBook]);

  const openPdf = useCallback((url: string, bookTitle: string) => {
    setPdfUrl(url);
    setPdfTitle(bookTitle);
  }, []);

  const closePdf = useCallback(() => {
    setPdfUrl(null);
    setPdfTitle('');
  }, []);

  const filteredBooks = tab === 'all' ? books : books.filter((b) => b.category === tab);

  return (
    <div className="page-section">
      <Header title="Reading Tracker" />

      {insights && <ReadingInsights insights={insights} />}

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowAdd(true)}>＋ Add Book</button>
        <button type="button" className="btn btn-ghost" onClick={() => setShowUpload(true)}>📤 New Upload</button>
      </div>

      <BookTabs value={tab} onChange={setTab} />

      {loading ? (
        <div className="card-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : filteredBooks.length === 0 ? (
        <EmptyState
          icon="📚"
          title="No books yet"
          message={tab === 'all' ? 'Add your first book or upload a PDF to get started.' : `No books in the "${tab}" category.`}
          action={<button type="button" className="btn btn-primary" onClick={() => setShowAdd(true)}>Add Book</button>}
        />
      ) : (
        <div className="card-grid">
          {filteredBooks.map((b) => (
            <BookCard
              key={b.id}
              book={b}
              onFinish={handleFinish}
              onStart={handleStart}
              onRemove={handleRemove}
              onOpen={(url) => openPdf(url, b.title)}
            />
          ))}
        </div>
      )}

      {/* Add Book modal */}
      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Add Book</h2>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '0.3rem' }}>Title *</label>
            <input
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Book title"
              onKeyDown={(e) => e.key === 'Enter' && void handleAdd()}
              style={{ width: '100%', marginBottom: '0.75rem' }}
            />
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '0.3rem' }}>Author</label>
            <input
              className="form-input"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="Author name"
              style={{ width: '100%', marginBottom: '0.75rem' }}
            />
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '0.3rem' }}>Category</label>
            <select
              className="form-input"
              value={category}
              onChange={(e) => setCategory(e.target.value as 'reading' | 'finished' | 'want')}
              style={{ width: '100%', marginBottom: '1.25rem' }}
            >
              <option value="reading">Reading</option>
              <option value="finished">Finished</option>
              <option value="want">Want to Read</option>
            </select>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={() => void handleAdd()}>Add Book</button>
            </div>
          </div>
        </div>
      )}

      {/* Upload modal */}
      {showUpload && (
        <div className="modal-overlay" onClick={() => setShowUpload(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Upload PDF</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Select a .pdf file to upload and add to your reading list.</p>
            <input
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              disabled={uploading}
              style={{ marginBottom: '1.25rem' }}
            />
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowUpload(false)} disabled={uploading}>Cancel</button>
              <button type="button" className="btn btn-primary" disabled>Upload</button>
            </div>
          </div>
        </div>
      )}

      {/* PDF Reader overlay */}
      {pdfUrl && (
        <PDFReader url={pdfUrl} title={pdfTitle} onClose={closePdf} />
      )}
    </div>
  );
};