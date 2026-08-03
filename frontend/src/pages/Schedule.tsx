import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { ScheduleEvent } from '../services/api';
import { TimetableGrid } from '../components/timetable/TimetableGrid';

export const Schedule = () => {
  const [searchParams] = useSearchParams();
  const [entries, setEntries] = useState<ScheduleEvent[]>([]);

  useEffect(() => {
    const day = searchParams.get('day_of_week');
    endpoints.schedule.list(day !== null ? Number(day) : undefined).then(setEntries).catch(() => {});
  }, [searchParams]);

  return (
    <div>
      <Header title="Schedule" />
      <div className="card">
        <TimetableGrid entries={entries} />
      </div>
    </div>
  );
};
