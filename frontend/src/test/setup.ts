import '@testing-library/jest-dom/vitest';

// sigma's bundle reads WebGL enum constants off these globals at module scope;
// jsdom does not define them, so provide stubs carrying the values sigma uses.
globalThis.WebGLRenderingContext = class {
  static TRIANGLES = 0x0004;
} as unknown as typeof WebGLRenderingContext;
globalThis.WebGL2RenderingContext = class {
  static BOOL = 0x8b56;
  static BYTE = 0x1400;
  static UNSIGNED_BYTE = 0x1401;
  static SHORT = 0x1402;
  static UNSIGNED_SHORT = 0x1403;
  static INT = 0x1404;
  static UNSIGNED_INT = 0x1405;
  static FLOAT = 0x1406;
} as unknown as typeof WebGL2RenderingContext;
