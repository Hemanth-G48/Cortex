import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { endpoints } from '../../services/api';
import type { EnrollmentSummary, KbStats } from '../../services/api';

interface NavCard {
  to: string;
  title: string;
  sub: string;
  icon: string;
}

/**
 * The cards themselves are fixed app routes (they are navigation, not data),
 * but their *content and order* are seeded from the live account state
 * (defect #63): the enrolled program/subject is surfaced on the Goal Tracker
 * card and the sections linked to the busiest vault areas float to the front.
 */
const CARDS: NavCard[] = [
  { to: '/life-areas', title: 'Wheel of Life', sub: 'Balance your life dimensions', icon: '🎡' },
  { to: '/goals', title: 'Goal Tracker', sub: 'Quarterly goals & progress', icon: '🎯' },
  { to: '/life-planner', title: 'Eisenhower Matrix', sub: 'Prioritize urgent vs important', icon: '🗂️' },
  { to: '/habits', title: 'Habit Tracker', sub: 'Build daily routines', icon: '🔄' },
  { to: '/journal', title: 'Daily Journal', sub: 'Capture your thoughts', icon: '📔' },
  { to: '/notes', title: 'Reflection Diary', sub: 'Review and reflect', icon: '📓' },
];

export const LifeNavigationGrid = () => {
  const [enrollment, setEnrollment] = useState<EnrollmentSummary | null>(null);
  const [vaultStats, setVaultStats] = useState<KbStats | null>(null);

  useEffect(() => {
    endpoints.enrollment.summary().then(setEnrollment).catch(() => setEnrollment(null));
    endpoints.kb.stats().then(setVaultStats).catch(() => setVaultStats(null));
  }, []);

  const cards = useMemo(() => {
    const vaultActivity =
      (vaultStats?.document_count ?? 0) + (vaultStats?.concept_count ?? 0);

    const seeded = CARDS.map((card) => {
      if (card.to === '/goals' && enrollment?.program_name) {
        // Real enrolled program (GET /enrollment/summary) instead of the
        // generic subtitle.
        const subjects = enrollment.subjects.length;
        return {
          ...card,
          sub: `${enrollment.program_name} · ${subjects} subject${subjects === 1 ? '' : 's'}`,
        };
      }
      if (card.to === '/notes' && vaultActivity > 0) {
        return { ...card, sub: `${vaultActivity} live vault signals` };
      }
      return card;
    });

    // Put the goal card first once a program is known — it is the section with
    // live account context to show.
    if (enrollment?.program_name) {
      const goals = seeded.find((c) => c.to === '/goals');
      if (goals) {
        return [goals, ...seeded.filter((c) => c.to !== '/goals')];
      }
    }
    return seeded;
  }, [enrollment, vaultStats]);

  return (
    <div>
      <div className="lp-section-title">Life Navigation</div>
      <div className="life-nav-grid">
        {cards.map((c) => (
          <Link key={c.to} to={c.to} className="life-nav-card">
            <span className="lnc-icon">{c.icon}</span>
            <span className="lnc-title">{c.title}</span>
            <span className="lnc-sub">{c.sub}</span>
          </Link>
        ))}
      </div>
    </div>
  );
};
