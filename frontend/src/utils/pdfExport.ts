// PDF export (99-phase plan, Phase 14 — ported from Shiori-v1 `utils/pdfExport.js`).
import { jsPDF } from 'jspdf';

const COLORS = {
  bg: [16, 20, 26],
  primary: [175, 198, 255],
  purple: [196, 77, 255],
  green: [77, 255, 145],
  orange: [255, 214, 160],
  text: [223, 226, 235],
  muted: [96, 96, 128],
  border: [42, 47, 60],
} as const;

const addRect = (doc: jsPDF, x: number, y: number, w: number, h: number, color: readonly number[]) => {
  doc.setFillColor(color[0], color[1], color[2]);
  doc.rect(x, y, w, h, 'F');
};

export interface PDFAssignment {
  title: string;
  courseName?: string | null;
  due_date?: string | null;
  status?: string;
}

export interface PDFStudyPlanWeek {
  week: number;
  topic: string;
  tasks: string[];
}

/** Render a week-by-week study plan as a dark-themed PDF. */
export const exportStudyPlanToPDF = (subject: string, examDate: string | null, weeks: PDFStudyPlanWeek[], appName = 'Student Life OS') => {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const W = 210;
  const H = 297;
  const margin = 14;
  const contentW = W - margin * 2;
  let y = 0;

  addRect(doc, 0, 0, W, H, COLORS.bg);
  addRect(doc, 0, 0, W, 28, [24, 28, 40]);
  doc.setTextColor(COLORS.primary[0], COLORS.primary[1], COLORS.primary[2]);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.text(appName, margin, 13);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(COLORS.muted[0], COLORS.muted[1], COLORS.muted[2]);
  doc.text('Study Plan Export', margin, 21);
  doc.text(new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }), W - margin, 21, { align: 'right' });
  y = 36;

  // Title
  doc.setTextColor(COLORS.text[0], COLORS.text[1], COLORS.text[2]);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.text(subject.slice(0, 60), margin, y);
  y += 7;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(COLORS.muted[0], COLORS.muted[1], COLORS.muted[2]);
  doc.text(examDate ? `Exam date: ${examDate}` : 'No exam date set', margin, y);
  y += 10;

  weeks.forEach((w) => {
    if (y > H - 50) {
      doc.addPage();
      addRect(doc, 0, 0, W, H, COLORS.bg);
      y = 14;
    }

    // Week header
    addRect(doc, margin, y, contentW, 8, [30, 35, 48]);
    doc.setTextColor(COLORS.primary[0], COLORS.primary[1], COLORS.primary[2]);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.text(`WEEK ${w.week} — ${w.topic.toUpperCase().slice(0, 40)}`, margin + 4, y + 5.5);
    y += 10;

    w.tasks.forEach((task) => {
      if (y > H - 20) {
        doc.addPage();
        addRect(doc, 0, 0, W, H, COLORS.bg);
        y = 14;
      }
      doc.setTextColor(COLORS.text[0], COLORS.text[1], COLORS.text[2]);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      const lines = doc.splitTextToSize(`•  ${task}`, contentW - 8);
      doc.text(lines, margin + 4, y + 3);
      y += 3 + lines.length * 3.6;
    });
    y += 6;
  });

  doc.setFillColor(24, 28, 40);
  doc.rect(0, H - 14, W, 14, 'F');
  doc.setTextColor(COLORS.muted[0], COLORS.muted[1], COLORS.muted[2]);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.text(appName, margin, H - 6);
  doc.text(`${weeks.length} weeks`, W - margin, H - 6, { align: 'right' });

  doc.save(`slos-study-plan-${subject.replace(/[^a-z0-9]+/gi, '-').toLowerCase() || 'plan'}.pdf`);
};

export const exportAssignmentsToPDF = (assignments: PDFAssignment[], appName = 'Student Life OS') => {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const W = 210;
  const H = 297;
  const margin = 14;
  const contentW = W - margin * 2;
  let y = 0;

  addRect(doc, 0, 0, W, H, COLORS.bg);

  // Header bar
  addRect(doc, 0, 0, W, 28, [24, 28, 40]);
  doc.setTextColor(COLORS.primary[0], COLORS.primary[1], COLORS.primary[2]);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.text(appName, margin, 13);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(COLORS.muted[0], COLORS.muted[1], COLORS.muted[2]);
  doc.text('Assignment List Export', margin, 21);
  doc.text(
    new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
    W - margin,
    21,
    { align: 'right' }
  );
  y = 36;

  // Column headers
  addRect(doc, margin, y, contentW, 7, [30, 35, 48]);
  const cols = [
    { label: 'ASSIGNMENT', x: margin + 3 },
    { label: 'COURSE', x: margin + 76 },
    { label: 'DUE DATE', x: margin + 128 },
    { label: 'STATUS', x: margin + 160 },
  ];
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(6.5);
  cols.forEach((col) => {
    doc.setTextColor(COLORS.muted[0], COLORS.muted[1], COLORS.muted[2]);
    doc.text(col.label, col.x, y + 4.5);
  });
  y += 9;

  const pending = assignments
    .filter((a) => a.status !== 'Completed' && a.status !== 'Graded')
    .sort((a, b) => new Date(a.due_date ?? 0).getTime() - new Date(b.due_date ?? 0).getTime());
  const completed = assignments.filter((a) => a.status === 'Completed' || a.status === 'Graded');
  const all = [...pending, ...completed];

  all.forEach((a, i) => {
    if (y > H - 20) {
      doc.addPage();
      addRect(doc, 0, 0, W, H, COLORS.bg);
      y = 14;
    }
    const rowBg = i % 2 === 0 ? [20, 24, 32] : [24, 28, 38];
    addRect(doc, margin, y, contentW, 8, rowBg);

    const isDone = a.status === 'Completed' || a.status === 'Graded';
    const statusColor = isDone ? COLORS.green : COLORS.orange;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(isDone ? COLORS.muted[0] : COLORS.text[0], isDone ? COLORS.muted[1] : COLORS.text[1], isDone ? COLORS.muted[2] : COLORS.text[2]);
    doc.text((a.title || '').slice(0, 38), margin + 3, y + 5);

    doc.setFontSize(7);
    doc.setTextColor(COLORS.muted[0], COLORS.muted[1], COLORS.muted[2]);
    doc.text((a.courseName || '').slice(0, 22), margin + 76, y + 5);
    doc.text(
      a.due_date ? new Date(a.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—',
      margin + 128,
      y + 5
    );

    doc.setTextColor(statusColor[0], statusColor[1], statusColor[2]);
    doc.text((a.status || 'pending').toUpperCase().slice(0, 12), margin + 160, y + 5);

    y += 9;
  });

  // Footer
  doc.setFillColor(24, 28, 40);
  doc.rect(0, H - 14, W, 14, 'F');
  doc.setTextColor(COLORS.muted[0], COLORS.muted[1], COLORS.muted[2]);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.text(appName, margin, H - 6);
  doc.text(`${all.length} assignments · ${pending.length} pending`, W - margin, H - 6, { align: 'right' });

  doc.save(`slos-assignments-${new Date().toISOString().split('T')[0]}.pdf`);
};
