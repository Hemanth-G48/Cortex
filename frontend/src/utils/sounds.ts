// Pomodoro sounds (99-phase plan, Phase 15 — ported from Shiori-v1 `utils/sounds.js`).
// Pure WebAudio — no assets, no permission needed.

let ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  try {
    if (!ctx) {
      const AC = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    return ctx;
  } catch {
    return null;
  }
}

export function playDing(type: 'focus' | 'break' | 'long-break' = 'focus') {
  const ac = getCtx();
  if (!ac) return;
  try {
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.connect(gain);
    gain.connect(ac.destination);

    if (type === 'break' || type === 'long-break') {
      // Higher, cheerful double-ding for break start
      osc.frequency.setValueAtTime(880, ac.currentTime);
      osc.frequency.setValueAtTime(1046, ac.currentTime + 0.15);
    } else {
      // Lower warm tone for focus start
      osc.frequency.setValueAtTime(528, ac.currentTime);
      osc.frequency.setValueAtTime(440, ac.currentTime + 0.2);
    }

    gain.gain.setValueAtTime(0, ac.currentTime);
    gain.gain.linearRampToValueAtTime(0.25, ac.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.9);
    osc.start(ac.currentTime);
    osc.stop(ac.currentTime + 0.9);
  } catch {
    // Audio is best-effort; never crash the timer.
  }
}
