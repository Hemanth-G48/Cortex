import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Route code-splitting (React.lazy in App.tsx) already gives every page its
// own chunk. This groups the shared node_modules deps into a few stable
// vendor chunks so repeat visits hit cache and no single chunk blows past the
// 500 kB warning threshold.
function vendorChunks(id: string): string | undefined {
  if (!id.includes('node_modules')) return undefined
  // Recharts + its d3 internals — the heaviest shared dependency, used by
  // Analytics/Grades/habit charts etc. Currently ~392 kB (78% of the 500 kB
  // warning ceiling); if a future recharts bump pushes it over, split d3
  // into its own chunk.
  if (id.includes('recharts') || id.includes('/d3-') || id.includes('/d3/') || id.includes('victory-vendor')) {
    return 'vendor-charts'
  }
  // PDF/print stack — jspdf itself, then its raster/SVG/sanitize deps. Split
  // into two chunks so neither trips the 500 kB warning (jspdf 4.x is heavy).
  if (id.includes('jspdf')) {
    return 'vendor-pdf'
  }
  if (id.includes('html2canvas') || id.includes('canvg') || id.includes('dompurify') || id.includes('/purify') || id.includes('css-line-break') || id.includes('text-segmentation') || id.includes('stackblur') || id.includes('svg-pathdata') || id.includes('rgbcolor') || id.includes('/core-js')) {
    return 'vendor-doc'
  }
  // Knowledge-graph rendering (sigma + graphology) — only the graph page needs it.
  if (id.includes('/sigma') || id.includes('graphology')) {
    return 'vendor-graph'
  }
  // React runtime + router — shared by every route.
  if (id.includes('/react/') || id.includes('/react-dom/') || id.includes('/scheduler/') || id.includes('/react-router') || id.includes('/history/') || id.includes('react-is') || id.includes('@remix-run')) {
    return 'vendor-react'
  }
  // Everything else (date-fns, etc.) in one shared chunk.
  return 'vendor-misc'
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rolldownOptions: {
      output: {
        manualChunks: vendorChunks,
      },
    },
  },
})
