import { useState, useEffect } from 'react';

/** Live digital clock shown in the sidebar */
export const DigitalClock = () => {
  const [time, setTime] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const hh = String(time.getHours()).padStart(2, '0');
  const mm = String(time.getMinutes()).padStart(2, '0');
  const ss = String(time.getSeconds()).padStart(2, '0');

  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  return (
    <div className="sidebar-widget digital-clock">
      <div className="clock-time">{hh}:{mm}<span className="clock-seconds">{ss}</span></div>
      <div className="clock-date">{days[time.getDay()]}, {months[time.getMonth()]} {time.getDate()}</div>
    </div>
  );
};
