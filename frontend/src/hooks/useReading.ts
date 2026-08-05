import { useCallback, useEffect, useState } from 'react';
import { bookApi, type Book, type BookInsights } from '../services/api';

interface UseReadingReturn {
  books: Book[];
  insights: BookInsights | null;
  loading: boolean;
  refresh: () => Promise<void>;
  addBook: (title: string, author: string | null, category: 'reading' | 'finished' | 'want') => Promise<void>;
  updateBook: (id: number, partial: Partial<Pick<Book, 'title' | 'author' | 'category'>>) => Promise<void>;
  removeBook: (id: number) => Promise<void>;
  setCategory: (c: 'all' | 'reading' | 'finished' | 'want') => void;
  category: 'all' | 'reading' | 'finished' | 'want';
  page: number;
  setPage: (p: number) => void;
}

export const useReading = (): UseReadingReturn => {
  const [books, setBooks] = useState<Book[]>([]);
  const [insights, setInsights] = useState<BookInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState<'all' | 'reading' | 'finished' | 'want'>('all');
  const [page, setPage] = useState(1);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const params: { category?: 'reading' | 'finished' | 'want'; page?: number; page_size?: number } = {};
      if (category !== 'all') params.category = category;
      params.page = page;
      params.page_size = 20;
      const res = await bookApi.list(params);
      setBooks(res.items);
      const ins = await bookApi.insights();
      setInsights(ins);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [category, page]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const addBook = useCallback(async (title: string, author: string | null, cat: 'reading' | 'finished' | 'want') => {
    await bookApi.create({ title, author, category: cat });
    await refresh();
  }, [refresh]);

  const updateBook = useCallback(async (id: number, partial: Partial<Pick<Book, 'title' | 'author' | 'category'>>) => {
    await bookApi.update(id, partial);
    await refresh();
  }, [refresh]);

  const removeBook = useCallback(async (id: number) => {
    await bookApi.remove(id);
    await refresh();
  }, [refresh]);

  const handleSetCategory = useCallback((c: 'all' | 'reading' | 'finished' | 'want') => {
    setCategory(c);
    setPage(1);
  }, []);

  const handleSetPage = useCallback((p: number) => {
    setPage(p);
  }, []);

  return {
    books,
    insights,
    loading,
    refresh,
    addBook,
    updateBook,
    removeBook,
    setCategory: handleSetCategory,
    category,
    page,
    setPage: handleSetPage,
  };
};