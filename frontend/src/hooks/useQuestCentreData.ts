import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';
import type {
  GamificationProfile,
  ProgressReport,
  PriorityWindow,
  QuestCentreCalendar,
  QuestCentreLifeArea,
  StatusWindow,
} from '../services/api';

export interface QuestCentreData {
  statusWindow: StatusWindow | null;
  progress: ProgressReport | null;
  priorityWindow: PriorityWindow | null;
  lifeAreas: QuestCentreLifeArea[];
  calendar: QuestCentreCalendar | null;
  gamification: GamificationProfile | null;
}

export interface QuestCentreHook {
  data: QuestCentreData;
  loading: boolean;
  errors: string[];
  refresh: () => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<QuestCentreData>>;
}

const EMPTY: QuestCentreData = {
  statusWindow: null,
  progress: null,
  priorityWindow: null,
  lifeAreas: [],
  calendar: null,
  gamification: null,
};

/**
 * Fetch every quest-centre dashboard payload in parallel and expose a single
 * ``{loading, errors, refresh, data}`` surface for the dashboard widgets.
 */
export const useQuestCentreData = (): QuestCentreHook => {
  const [data, setData] = useState<QuestCentreData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    const errs: string[] = [];
    const [sw, prog, pw, areas, cal, gam] = await Promise.allSettled([
      endpoints.questCentre.statusWindow(),
      endpoints.questCentre.progress(),
      endpoints.questCentre.priorityWindow(),
      endpoints.questCentre.lifeAreas(),
      endpoints.questCentre.calendar(),
      endpoints.questCentre.gamification(),
    ]);
    const ok = <T,>(r: PromiseSettledResult<T>): T | null => (r.status === 'fulfilled' ? r.value : null);
    if (sw.status === 'rejected') errs.push('status-window');
    if (prog.status === 'rejected') errs.push('progress');
    if (pw.status === 'rejected') errs.push('priority-window');
    if (areas.status === 'rejected') errs.push('life-areas');
    if (cal.status === 'rejected') errs.push('calendar');
    if (gam.status === 'rejected') errs.push('gamification');
    setData({
      statusWindow: ok(sw),
      progress: ok(prog),
      priorityWindow: ok(pw),
      lifeAreas: ok(areas) ?? [],
      calendar: ok(cal),
      gamification: ok(gam),
    });
    setErrors(errs);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, errors, refresh, setData };
};
