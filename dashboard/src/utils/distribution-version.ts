export interface DistributionVersion {
  major: number
  minor: number
  patch: number
}

export function parseDistributionVersion(value: string): DistributionVersion | null {
  const cleaned = value.trim().replace(/^v/i, '')
  const match = cleaned.match(/^(\d+)\.(\d+)\.(\d+)$/)
  if (!match) return null

  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3]),
  }
}

export function compareDistributionVersions(current: string, latest: string): number {
  const a = parseDistributionVersion(current)
  const b = parseDistributionVersion(latest)
  if (!a || !b) return 0

  const av = [a.major, a.minor, a.patch]
  const bv = [b.major, b.minor, b.patch]
  for (let i = 0; i < av.length; i++) {
    if (av[i] < bv[i]) return -1
    if (av[i] > bv[i]) return 1
  }
  return 0
}

export function normalizeDistributionVersion(value: string | null): string | null {
  if (!value) return null
  return value.trim().replace(/^v/i, '') || null
}
