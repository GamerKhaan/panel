import { describe, expect, test } from 'bun:test'
import { compareDistributionVersions, normalizeDistributionVersion, parseDistributionVersion } from './distribution-version'

describe('distribution version comparison', () => {
  test('treats official stock version as older than first owned AWG release', () => {
    expect(compareDistributionVersions('5.4.1', '5.4.1-awg31.1')).toBe(-1)
    expect(compareDistributionVersions('0.5.4', '0.5.4-awg31.1')).toBe(-1)
  })

  test('treats identical owned versions as equal', () => {
    expect(compareDistributionVersions('v5.4.1-awg31.1', '5.4.1-awg31.1')).toBe(0)
  })

  test('orders owned revision updates', () => {
    expect(compareDistributionVersions('5.4.1-awg31.1', '5.4.1-awg31.2')).toBe(-1)
    expect(compareDistributionVersions('5.4.1-awg31.2', '5.4.1-awg31.1')).toBe(1)
  })

  test('orders upstream base releases before distribution revision', () => {
    expect(compareDistributionVersions('5.4.1-awg31.9', '5.4.2-awg31.1')).toBe(-1)
  })

  test('normalizes only the leading v and preserves distribution suffix', () => {
    expect(normalizeDistributionVersion('v5.4.1-awg31.1')).toBe('5.4.1-awg31.1')
  })

  test('fails closed for unrelated version formats', () => {
    expect(parseDistributionVersion('not-a-version')).toBeNull()
    expect(compareDistributionVersions('not-a-version', '5.4.1-awg31.1')).toBe(0)
  })
})
