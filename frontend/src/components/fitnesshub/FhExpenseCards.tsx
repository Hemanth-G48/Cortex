import type { CSSProperties } from 'react';
import type { Expense, ExpenseSummary } from '../../services/api';

interface Props {
  expenses: Expense[];
  summary: ExpenseSummary;
  onDelete?: (id: number) => void;
}

const CAT_CLASS: Record<string, string> = {
  Supplement: 'supplement',
  Equipment: 'equipment',
  Gym: 'gym',
};

const CAT_COLOR: Record<string, string> = {
  Supplement: 'var(--fh-blue)',
  Equipment: 'var(--fh-yellow)',
  Gym: 'var(--fh-green)',
};

/** Row 4: Expenses (Phases 92-93, 96) — spec cards + donut breakdown. */
export const FhExpenseCards = ({ expenses, summary, onDelete }: Props) => {
  const { total, by_category } = summary;
  const cats = ['Supplement', 'Equipment', 'Gym'];
  let acc = 0;
  const segs = cats.map((c) => {
    const val = by_category[c] ?? 0;
    const start = acc;
    acc += val;
    return { cat: c, val, start, end: acc };
  });
  const pct = (v: number) => (total > 0 ? Math.round((v / total) * 100) : 0);
  const donutStyle: CSSProperties = {
    ['--d1' as string]: `${total > 0 ? (segs[0].end / total) * 100 : 0}%`,
    ['--d2' as string]: `${total > 0 ? (segs[1].end / total) * 100 : 0}%`,
  };

  return (
    <section className="fh-row" id="expenses">
      <div className="fh-section-title">Row 4 · Expenses</div>
      <div className="fh-expense-layout">
        <div className="fh-expense-row">
          {expenses.length === 0 && (
            <div className="fh-empty" style={{ gridColumn: '1 / -1' }}>
              <span className="fh-empty-icon" aria-hidden="true">💸</span>
              <span className="fh-empty-title">No expenses yet</span>
              <span>Add Protein & Creatine, Multivitamin, Liver Salt and Equipment costs.</span>
            </div>
          )}
          {expenses.map((e) => (
            <div key={e.id} className="fh-expense-card">
              <div className="fh-expense-title">{e.title}</div>
              <div className="fh-expense-cost">${e.cost.toFixed(2)}</div>
              <div className="fh-expense-meta">
                <span>{e.date}</span>
                <span className={`fh-tag ${CAT_CLASS[e.category] ?? 'supplement'}`}>{e.category}</span>
              </div>
              {onDelete && (
                <button
                  type="button"
                  className="fh-goal-edit"
                  style={{ alignSelf: 'flex-end' }}
                  onClick={() => onDelete(e.id)}
                  aria-label={`Delete ${e.title}`}
                >
                  🗑️
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="fh-donut-card">
          <div className="fh-donut" style={donutStyle}>
            <div className="fh-donut-label">
              <span className="fh-donut-total">${total.toFixed(0)}</span>
              <span className="fh-donut-cap">total spent</span>
            </div>
          </div>
          <div className="fh-donut-legend">
            {cats.map((c) => (
              <div key={c} className="fh-legend-row">
                <span>
                  <span className="fh-legend-dot" style={{ background: CAT_COLOR[c] }} />
                  {c}
                </span>
                <span className="fh-legend-pct">{pct(by_category[c] ?? 0)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
