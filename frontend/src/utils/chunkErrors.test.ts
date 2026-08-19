import { describe, it, expect } from 'vitest';
import { isChunkLoadError } from './chunkErrors';

describe('isChunkLoadError', () => {
  it('detects Vite dev dynamic-import failures', () => {
    const err = new TypeError(
      'Failed to fetch dynamically imported module: http://localhost:5173/src/pages/Courses.tsx',
    );
    expect(isChunkLoadError(err)).toBe(true);
  });

  it('detects Vite production dynamic-import failures (hashed assets)', () => {
    const err = new TypeError(
      'Failed to fetch dynamically imported module: http://localhost:5199/assets/Courses-AB12cd34.js',
    );
    expect(isChunkLoadError(err)).toBe(true);
  });

  it('detects webpack ChunkLoadError by name and message', () => {
    expect(isChunkLoadError(new Error('Loading chunk 42 failed.'))).toBe(true);
    const named = new Error('Loading CSS chunk 7 failed.');
    named.name = 'ChunkLoadError';
    expect(isChunkLoadError(named)).toBe(true);
  });

  it('detects Safari/WebKit module-script failures', () => {
    expect(isChunkLoadError(new Error('Importing a module script failed.'))).toBe(true);
  });

  it('does not flag ordinary render errors', () => {
    expect(isChunkLoadError(new TypeError('Cannot read properties of undefined (reading "map")'))).toBe(false);
    expect(isChunkLoadError(new Error('Unexpected token in JSON'))).toBe(false);
    expect(isChunkLoadError(new Error(''))).toBe(false);
  });
});
