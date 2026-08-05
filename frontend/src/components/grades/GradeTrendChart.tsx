import { useEffect, useRef } from 'react';
import type { Grade } from '../../services/api';

interface GradeTrendChartProps {
  grades: Grade[];
  /** Optional per-grade label shown under each point. */
  height?: number;
}

/**
 * Canvas trend chart of grade percentages (port of Shiori's GradeTrendChart).
 * Plots each grade's percentage in order and connects the dots; the dashed
 * line marks the 60% "passing" threshold. Pure presentational component.
 */
export const GradeTrendChart = ({ grades, height = 120 }: GradeTrendChartProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth || 400;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    const pts = grades
      .map((g) => ({ pct: g.points_possible > 0 ? (g.points_earned / g.points_possible) * 100 : null }))
      .filter((p): p is { pct: number } => p.pct !== null);

    // Pass threshold line
    ctx.strokeStyle = 'rgba(78, 205, 196, 0.35)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    const passY = height - (60 / 100) * (height - 16) - 8;
    ctx.moveTo(8, passY);
    ctx.lineTo(width - 8, passY);
    ctx.stroke();
    ctx.setLineDash([]);

    if (pts.length === 0) {
      ctx.fillStyle = 'var(--text-muted, #5f6368)';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No graded items yet', width / 2, height / 2);
      return;
    }

    const pad = 8;
    const max = Math.max(100, ...pts.map((p) => p.pct)) + 5;
    const x = (i: number) => pad + (pts.length === 1 ? (width - pad * 2) / 2 : (i * (width - pad * 2)) / (pts.length - 1));
    const y = (v: number) => height - 8 - (v / max) * (height - 24);

    // Area fill under the line
    ctx.beginPath();
    pts.forEach((p, i) => (i === 0 ? ctx.moveTo(x(i), y(p.pct)) : ctx.lineTo(x(i), y(p.pct))));
    ctx.lineTo(x(pts.length - 1), height - 8);
    ctx.lineTo(x(0), height - 8);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, 'rgba(108, 92, 231, 0.35)');
    grad.addColorStop(1, 'rgba(108, 92, 231, 0.02)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Trend line
    ctx.beginPath();
    pts.forEach((p, i) => (i === 0 ? ctx.moveTo(x(i), y(p.pct)) : ctx.lineTo(x(i), y(p.pct))));
    ctx.strokeStyle = 'var(--info, #6c5ce7)';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Points + labels
    pts.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(x(i), y(p.pct), 3.5, 0, Math.PI * 2);
      ctx.fillStyle = p.pct >= 60 ? 'var(--success, #4ecdc4)' : 'var(--danger, #e8496d)';
      ctx.fill();
      ctx.strokeStyle = 'var(--bg-card, #181a1c)';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = 'var(--text-muted, #5f6368)';
      ctx.font = '9px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${Math.round(p.pct)}%`, x(i), y(p.pct) - 8);
    });
  }, [grades, height]);

  return (
    <div style={{ width: '100%' }}>
      <canvas ref={canvasRef} style={{ width: '100%', height, display: 'block' }} />
    </div>
  );
};
