import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { KnowledgeBase } from '../pages/KnowledgeBase';

vi.mock('../services/api', () => {
  const sources = [
    {
      id: 1,
      user_id: 1,
      name: 'Obsidian Vault',
      source_type: 'vault_folder',
      root_path: '/home/me/vault',
      enabled: true,
      last_scanned_at: '2026-08-05T10:00:00',
      files_seen: 4,
      files_added: 2,
      files_changed: 1,
      files_removed: 0,
      created_at: '2026-08-01T00:00:00',
      document_count: 3,
    },
  ];

  const docs = [
    {
      id: 10,
      user_id: 1,
      source_id: 1,
      path_rel: 'notes/hello.md',
      title: 'hello',
      doc_type: 'md',
      content_hash: 'abc123',
      char_count: 1200,
      frontmatter: { title: 'Hello' },
      outline: [],
      metadata: { wikilinks: ['other-note'], tags: ['math'] },
      ocr_used: false,
      needs_ocr: false,
      status: 'unchanged',
      doc_date: null,
      created_at: '2026-08-05T10:00:00',
      updated_at: '2026-08-05T10:00:00',
      indexed_at: '2026-08-05T10:00:00',
      chunk_count: 2,
    },
  ];

  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({ user: null }),
      kb: {
        sources: {
          list: vi.fn().mockResolvedValue({ items: sources, total: 1 }),
          get: vi.fn(),
          create: vi.fn().mockResolvedValue(sources[0]),
          update: vi.fn().mockResolvedValue(sources[0]),
          remove: vi.fn().mockResolvedValue({ ok: true, deleted_documents: 3 }),
          scan: vi.fn().mockResolvedValue({
            job: { id: 1, job_type: 'scan', status: 'done', total_items: 1, processed_items: 1 },
            summary: { added: 1, changed: 0, duplicates_found: 0 },
          }),
        },
        documents: {
          list: vi.fn().mockResolvedValue({ items: docs, total: 1, page: 1, page_size: 100 }),
          get: vi.fn(),
          remove: vi.fn().mockResolvedValue({ ok: true }),
          upload: vi.fn().mockResolvedValue({ document: docs[0], deduped: false, duplicate_of_id: null }),
          chunks: vi.fn().mockResolvedValue([
            { id: 1, document_id: 10, seq: 0, content: 'chunk text', char_start: 0, char_end: 10, heading_path: 'Intro', token_estimate: 2 },
          ]),
          versions: vi.fn().mockResolvedValue([]),
          restore: vi.fn().mockResolvedValue({ document: docs[0], new_version_seq: 2 }),
          diff: vi.fn().mockResolvedValue({ from_version: 1, to_version: 2, changed: true, diff: '-old\n+new' }),
          reindex: vi.fn().mockResolvedValue({ id: 2, job_type: 'reindex', status: 'queued', total_items: 1, processed_items: 0 }),
        },
        papers: { import: vi.fn().mockResolvedValue({ document: docs[0], metadata_fetched: true }) },
        jobs: { list: vi.fn().mockResolvedValue({ items: [], total: 0 }), get: vi.fn() },
        stats: vi.fn().mockResolvedValue({
          document_count: 1,
          chunk_count: 2,
          embedding_count: 2,
          embedded_documents: 1,
          tag_count: 1,
          concept_count: 0,
          edge_count: 0,
          duplicate_count: 0,
          total_tokens: 10,
          embeddings_today: 0,
          embeddings_limit: 1000,
          inferences_today: 0,
          inference_limit: 100,
          dirty_documents: 0,
        }),
        related: {
          list: vi.fn().mockResolvedValue({ document_id: 10, related: [], method: 'embedding' }),
        },
        tags: {
          forDocument: vi.fn().mockResolvedValue({ document_id: 10, tags: [] }),
          apply: vi.fn().mockResolvedValue({ document_id: 10, tags: [] }),
          reject: vi.fn().mockResolvedValue({ ok: true, removed: 1 }),
        },
        concepts: {
          list: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
        },
        metadata: { update: vi.fn().mockResolvedValue({}) },
        duplicates: {
          list: vi.fn().mockResolvedValue({ items: [], total: 0, method: 'embedding' }),
          scan: vi.fn().mockResolvedValue({ items: [], total: 0, method: 'embedding' }),
          merge: vi.fn().mockResolvedValue({ ok: true, merged: 1 }),
          archive: vi.fn().mockResolvedValue({ ok: true }),
        },
        reindex: {
          source: vi.fn().mockResolvedValue({ id: 3, job_type: 'reindex', status: 'queued', total_items: 0, processed_items: 0 }),
          documents: vi.fn().mockResolvedValue({ id: 3, job_type: 'reindex', status: 'queued', total_items: 0, processed_items: 0 }),
          backfill: vi.fn().mockResolvedValue({ id: 3, job_type: 'reindex', status: 'queued', total_items: 0, processed_items: 0 }),
        },
      },
    },
  };
});

describe('Knowledge Base page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders sources, documents and action buttons', async () => {
    render(<KnowledgeBase />);
    await waitFor(() => expect(screen.getByText('/home/me/vault')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('hello')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Add Source/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload Document/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Import arXiv Paper/ })).toBeInTheDocument();
    // Status chips render inside the document rows (also present in the filter
    // dropdown, so assert via getAllByText).
    expect(screen.getAllByText('unchanged').length).toBeGreaterThanOrEqual(1);
  });

  it('shows a jobs empty state', async () => {
    render(<KnowledgeBase />);
    await waitFor(() => expect(screen.getByText('/home/me/vault')).toBeInTheDocument());
    expect(screen.getByText(/No jobs yet/)).toBeInTheDocument();
  });
});
