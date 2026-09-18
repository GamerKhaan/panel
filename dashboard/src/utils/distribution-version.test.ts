import { describe, expect, test } from 'bun:test'
import { compareDistributionVersions, normalizeDistributionVersion, parseDistributionVersion } from './distribution-version'

describe('distribution version comparison', () => {
  test('compares owned distribution releases as normal semver', () => {
    expect(compareDistributionVersions('1.0.0', '1.0.1')).toBe(-1)
    expect(compareDistributionVersions('1.1.0', '1.0.9')).toBe(1)
    expect(compareDistributionVersions('v1.0.0', '1.0.0')).toBe(0)
  })

  test('normalizes a leading v', () => {
    expect(normalizeDistributionVersion('v1.0.0')).toBe('1.0.0')
  })

  test('parses the first owned release', () => {
    expect(parseDistributionVersion('v1.0.0')).toEqual({ major: 1, minor: 0, patch: 0 })
  })

  test('fails closed for unrelated version formats', () => {
    expect(parseDistributionVersion('5.4.1-awg31.1')).toBeNull()
    expect(compareDistributionVersions('not-a-version', '1.0.0')).toBe(0)
  })
})
