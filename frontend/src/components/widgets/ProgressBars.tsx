/** Progress bars for academic periods */
export const ProgressBars = () => {
  const now = new Date();
  const yearStart = new Date(now.getFullYear(), 0, 1);
  const yearEnd = new Date(now.getFullYear() + 1, 0, 1);
  const yearPct = Math.round(((now.getTime() - yearStart.getTime()) / (yearEnd.getTime() - yearStart.getTime())) * 100);

  const monthDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const monthPct = Math.round(((now.getDate() - 1) / monthDays) * 100);

  const weekDays = now.getDay();
  const weekPct = Math.round((weekDays / 7) * 100);

  return (
    <div className="sidebar-widget progress-bars">
      <div className="widget-title">Progress</div>

      <div className="pb-row">
        <span className="pb-label">Year</span>
        <div className="xp-bar"><div className="xp-fill" style={{ width: `${yearPct}%` }} /></div>
        <span className="pb-value">{yearPct}%</span>
      </div>

      <div className="pb-row">
        <span className="pb-label">Month</span>
        <div className="xp-bar"><div className="xp-fill" style={{ width: `${monthPct}%` }} /></div>
        <span className="pb-value">{monthPct}%</span>
      </div>

      <div className="pb-row">
        <span className="pb-label">Week</span>
        <div className="xp-bar"><div className="xp-fill" style={{ width: `${weekPct}%` }} /></div>
        <span className="pb-value">{weekPct}%</span>
      </div>
    </div>
  );
};
