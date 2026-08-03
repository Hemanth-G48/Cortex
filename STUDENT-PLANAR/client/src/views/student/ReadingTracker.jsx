import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function ReadingTracker({ studentId }) {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentTab, setCurrentTab] = useState('all'); // all, topics, finished, insights
  const [pdfUrl, setPdfUrl] = useState(null);

  const fetchBooks = async () => {
    try {
      const res = await axios.get(`http://localhost:5000/api/books/${studentId}`);
      setBooks(res.data);
      setLoading(false);
    } catch (err) { console.error(err); setLoading(false); }
  };

  useEffect(() => {
    fetchBooks();
  }, [studentId]);

  const updateStatus = async (bookId, newCategory) => {
    try {
      await axios.put(`http://localhost:5000/api/books/${bookId}`, { category: newCategory });
      fetchBooks();
    } catch (err) { console.error(err); }
  };

  const deleteBook = async (bookId) => {
    if (!confirm('Are you sure you want to remove this book?')) return;
    try {
      await axios.delete(`http://localhost:5000/api/books/${bookId}`);
      fetchBooks();
    } catch (err) { console.error(err); }
  };

  const renderBookGrid = (bookList) => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '1.5rem' }}>
      {bookList.map(book => (
        <div key={book._id} className="book-card" style={{ 
          backgroundColor: 'var(--bg-color-secondary)', 
          borderRadius: '12px', 
          overflow: 'hidden', 
          border: '1px solid var(--border-color)',
          transition: '0.3s',
          cursor: 'pointer'
        }}>
          <div style={{ position: 'relative', width: '100%', aspectRatio: '2/3', background: '#222' }}>
            <img src={book.coverUrl} alt={book.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            <div className="book-overlay" style={{ 
              position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', opacity: 0, transition: '0.3s', padding: '1rem', textAlign: 'center'
            }}>
              {book.fileUrl && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setPdfUrl(`http://localhost:5000${book.fileUrl}`); }}
                  style={{ backgroundColor: 'var(--accent-orange)', border: 'none', color: '#000', padding: '6px 12px', borderRadius: '4px', marginBottom: '8px', width: '100%', cursor: 'pointer', fontWeight: 'bold' }}
                >
                  📖 Read File
                </button>
              )}
              {book.category !== 'finished' && (
                <button onClick={() => updateStatus(book._id, 'finished')} style={{ backgroundColor: 'var(--accent-green)', border: 'none', color: '#000', padding: '6px 12px', borderRadius: '4px', marginBottom: '8px', width: '100%', cursor: 'pointer', fontWeight: 'bold' }}>
                  Mark Finished
                </button>
              )}
              {book.category !== 'reading' && (
                <button onClick={() => updateStatus(book._id, 'reading')} style={{ backgroundColor: 'var(--accent-blue)', border: 'none', color: 'white', padding: '6px 12px', borderRadius: '4px', marginBottom: '8px', width: '100%', cursor: 'pointer' }}>
                  Start Reading
                </button>
              )}
              <button onClick={() => deleteBook(book._id)} style={{ backgroundColor: 'transparent', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', padding: '6px 12px', borderRadius: '4px', width: '100%', cursor: 'pointer' }}>
                Remove
              </button>
            </div>
          </div>
          <div style={{ padding: '0.8rem' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{book.title}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{book.author}</div>
          </div>
        </div>
      ))}
      {bookList.length === 0 && (
        <div style={{ gridColumn: '1/-1', border: '1px dashed var(--border-color)', borderRadius: '12px', height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
           <span>No books found in this view</span>
        </div>
      )}
    </div>
  );

  const renderContent = () => {
    if (loading) return <p>Loading your library...</p>;

    switch (currentTab) {
      case 'all':
        return (
          <>
            <section style={{ marginBottom: '3rem' }}>
              <h3 style={{ textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '2px', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Currently Reading</h3>
              {renderBookGrid(books.filter(b => b.category === 'reading'))}
            </section>
            <section style={{ marginBottom: '3rem' }}>
              <h3 style={{ textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '2px', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Want to Read</h3>
              {renderBookGrid(books.filter(b => b.category === 'want'))}
            </section>
          </>
        );
      case 'finished':
        return (
          <section>
             <h3 style={{ textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '2px', color: 'var(--accent-green)', marginBottom: '1.5rem' }}>Completed Works</h3>
             {renderBookGrid(books.filter(b => b.category === 'finished'))}
          </section>
        );
      case 'topics':
        // Simple grouping by author for "topics"
        const groups = books.reduce((acc, book) => {
          (acc[book.author] = acc[book.author] || []).push(book);
          return acc;
        }, {});
        return Object.entries(groups).map(([author, authorBooks]) => (
          <section key={author} style={{ marginBottom: '3rem' }}>
            <h3 style={{ textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '2px', color: 'var(--accent-blue)', marginBottom: '1.5rem' }}>By: {author}</h3>
            {renderBookGrid(authorBooks)}
          </section>
        ));
      case 'insights':
        const stats = {
          total: books.length,
          finished: books.filter(b => b.category === 'finished').length,
          reading: books.filter(b => b.category === 'reading').length,
          want: books.filter(b => b.category === 'want').length
        };
        return (
          <div className="insights-view" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem' }}>
             <div style={{ backgroundColor: 'var(--bg-color-secondary)', padding: '2rem', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                <div style={{ fontSize: '3rem', color: 'var(--accent-blue)', fontWeight: 'bold' }}>{stats.total}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Total Books</div>
             </div>
             <div style={{ backgroundColor: 'var(--bg-color-secondary)', padding: '2rem', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                <div style={{ fontSize: '3rem', color: 'var(--accent-green)', fontWeight: 'bold' }}>{stats.finished}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Finished</div>
             </div>
             <div style={{ backgroundColor: 'var(--bg-color-secondary)', padding: '2rem', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                <div style={{ fontSize: '3rem', color: 'var(--accent-orange)', fontWeight: 'bold' }}>{stats.reading}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Reading Now</div>
             </div>
             <div style={{ backgroundColor: 'var(--bg-color-secondary)', padding: '2rem', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                <div style={{ fontSize: '3rem', color: 'var(--accent-purple)', fontWeight: 'bold' }}>{stats.want}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Wishlist</div>
             </div>
             <div style={{ gridColumn: '1/-1', marginTop: '2rem', padding: '2rem', backgroundColor: 'var(--bg-color-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <h3>Reading Consistency</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>You have completed {((stats.finished / stats.total) * 100 || 0).toFixed(1)}% of your library!</p>
                <div style={{ width: '100%', height: '10px', backgroundColor: '#333', borderRadius: '5px', marginTop: '1rem', overflow: 'hidden' }}>
                   <div style={{ width: `${(stats.finished / stats.total) * 100 || 0}%`, height: '100%', backgroundColor: 'var(--accent-green)', boxShadow: '0 0 10px var(--accent-green)' }}></div>
                </div>
             </div>
          </div>
        );
      default: return null;
    }
  };

  return (
    <div className="reading-tracker" style={{ padding: '1rem', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '2.5rem', fontStyle: 'italic' }}>Reading Tracker</h2>
      </div>

      <div style={{ display: 'flex', gap: '2rem', marginBottom: '2rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
        {['all', 'topics', 'finished', 'insights'].map(tab => (
          <span 
            key={tab}
            onClick={() => setCurrentTab(tab)}
            style={{ 
              borderBottom: currentTab === tab ? '2px solid var(--accent-blue)' : 'none', 
              color: currentTab === tab ? 'var(--text-primary)' : 'var(--text-secondary)', 
              paddingBottom: '4px', 
              cursor: 'pointer',
              textTransform: 'capitalize',
              transition: '0.3s'
            }}
          >
            {tab === 'all' ? 'All Books' : tab}
          </span>
        ))}
      </div>

      {renderContent()}

      <style>{`
        .book-card:hover .book-overlay { opacity: 1 !important; }
        .book-card:hover { transform: translateY(-5px); border-color: var(--accent-blue) !important; box-shadow: 0 10px 20px rgba(0,136,255,0.1); }
      `}</style>

      {/* Full Screen PDF Reader Modal */}
      {pdfUrl && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.9)', zIndex: 9999, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#111', borderBottom: '1px solid var(--accent-orange)' }}>
             <h3 style={{ color: 'var(--accent-orange)', margin: 0, letterSpacing: '2px' }}>📖 reading mode</h3>
             <button onClick={() => setPdfUrl(null)} style={{ background: 'none', border: 'none', color: 'var(--accent-red)', fontSize: '1.5rem', cursor: 'pointer' }}>✕ Close</button>
          </div>
          <iframe 
            src={pdfUrl} 
            style={{ flex: 1, width: '100%', border: 'none', backgroundColor: '#fff' }} 
            title="PDF Reader"
          />
        </div>
      )}

    </div>
  );
}
