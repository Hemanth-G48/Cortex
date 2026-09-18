/**
 * Match LifeArea rows to their vault domains so non-study surfaces can show
 * how much Second Brain material backs each area (audit defect #83).
 *
 * Domains come from ``GET /api/kb/domains`` (top-level ``KbFolder`` rows with a
 * live ``doc_count``). There is no stored area↔domain mapping, so we match on
 * shared name tokens: an area "Fitness" matches a domain "Fitness" or
 * "Health & Fitness". Areas with no match return ``null`` (no spark shown)
 * rather than a misleading zero.
 */

export interface VaultDomainLike {
  name: string;
  doc_count: number;
}

const STOPWORDS = new Set(['and', 'or', 'the', 'of', 'a', 'an', 'to', 'in', 'for']);

const tokens = (value: string): string[] =>
  value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length > 1 && !STOPWORDS.has(t));

/** Distinct-by-token domains that overlap the area name (exact token match). */
export function domainsForArea(
  areaName: string,
  domains: VaultDomainLike[],
): VaultDomainLike[] {
  const areaTokens = new Set(tokens(areaName));
  if (areaTokens.size === 0) return [];
  const direct = domains.filter((d) => tokens(d.name).some((t) => areaTokens.has(t)));
  if (direct.length > 0) return direct;
  // Fall back to a substring match in either direction ("Finances" ↔ "Finance").
  const lower = areaName.toLowerCase();
  return domains.filter((d) => {
    const dn = d.name.toLowerCase();
    return dn.length > 2 && (lower.includes(dn) || dn.includes(lower));
  });
}

/** Summed document count for an area, or ``null`` when no domain maps to it. */
export function areaDocCount(
  areaName: string,
  domains: VaultDomainLike[],
): number | null {
  const matched = domainsForArea(areaName, domains);
  if (matched.length === 0) return null;
  return matched.reduce((s, d) => s + (d.doc_count || 0), 0);
}
