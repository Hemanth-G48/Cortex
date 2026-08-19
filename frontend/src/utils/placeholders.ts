/** Coloured SVG data URI for a course thumbnail card */
export const courseThumbnail = (title: string, hue?: number): string => {
  const h = hue ?? Math.abs(title.split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % 360;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="140">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:hsl(${h},60%,30%)"/>
      <stop offset="100%" style="stop-color:hsl(${(h + 60) % 360},60%,20%)"/>
    </linearGradient></defs>
    <rect width="320" height="140" fill="url(#g)" rx="8"/>
    <text x="16" y="80" fill="rgba(255,255,255,0.95)" font-size="22" font-weight="700" font-family="Inter,sans-serif">${escapeXml(title)}</text>
  </svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
};

/** Simple emoji-based resource icon (no SVG needed for these) */
export const resourceIcon = (type: string): string => {
  switch (type.toLowerCase()) {
    case 'pdf': case 'document': return '📄';
    case 'video': return '🎬';
    case 'link': case 'url': return '🔗';
    case 'code': case 'github': return '💻';
    case 'quiz': return '📝';
    case 'folder': case 'drive': return '📁';
    case 'classroom': return '🏫';
    default: return '📎';
  }
};

/** CSS gradient string for a banner */
export const bannerGradient = (hue = 340): string =>
  `linear-gradient(135deg, hsl(${hue},70%,25%), hsl(${(hue + 50) % 360},60%,15%))`;

/* ----- helpers ----- */
const escapeXml = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
