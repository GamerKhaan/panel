import { describe, expect, it } from 'bun:test'
import { generateWireGuardKeyPair } from '@pasarguard/core-kit/wireguard'
import { amneziaWGConfigToDraft, amneziaWGDraftToConfig, createNewAmneziaWGDraft, regenerateAmneziaWGKeys } from './amneziawg-adapter'

describe('AmneziaWG form adapter', () => {
  it('creates a new draft with a usable keypair', () => {
    const draft = createNewAmneziaWGDraft()
    expect(draft.privateKey).not.toBe('')
    expect(draft.publicKey).not.toBe('')
  })

  it('round-trips existing keys, unknown envelope data, zero and false losslessly', () => {
    const pair = generateWireGuardKeyPair()
    const raw = {
      schema_version: 1,
      implementation: 'GamerKhaan/pasarguard-awg31-patch',
      interface_name: 'awg-existing',
      private_key: pair.privateKey,
      public_key: pair.publicKey,
      listen_port: 0,
      address: ['10.70.0.1/24'],
      awg: { jc: 0, jmin: 0, jmax: 0, s1: 16, s2: 16, s3: 16, s4: 16, h1: '1', h2: '2', h3: '3', h4: '4', content_padding_addition: '0', random_trailers: false, disable_cookies: false },
      future_envelope: { enabled: false, count: 0 },
    }
    const parsed = amneziaWGConfigToDraft(raw)
    expect(parsed.ok).toBe(true)
    if (!parsed.ok) return
    const output = amneziaWGDraftToConfig(parsed.draft)
    expect(output).toEqual(raw)
    expect(parsed.draft.privateKey).toBe(pair.privateKey)
    const regenerated = regenerateAmneziaWGKeys(parsed.draft)
    expect(regenerated.privateKey).not.toBe(pair.privateKey)
    expect(regenerated.publicKey).not.toBe(pair.publicKey)
  })

  it('refuses an unsupported version instead of rewriting it', () => {
    expect(amneziaWGConfigToDraft({ schema_version: 2, implementation: 'future', awg: {} }).ok).toBe(false)
  })

  it('preserves absent, null, and empty pre-shared-key states', () => {
    const pair = generateWireGuardKeyPair()
    const base = {
      schema_version: 1,
      implementation: 'GamerKhaan/pasarguard-awg31-patch',
      interface_name: 'awg0', private_key: pair.privateKey, public_key: pair.publicKey,
      listen_port: 51820, address: ['10.70.0.1/24'], awg: {},
    }
    for (const raw of [base, { ...base, pre_shared_key: null }, { ...base, pre_shared_key: '' }]) {
      const parsed = amneziaWGConfigToDraft(raw)
      expect(parsed.ok).toBe(true)
      if (parsed.ok) expect(amneziaWGDraftToConfig(parsed.draft)).toEqual(raw)
    }
  })

  it('defines every required AmneziaWG advanced field', async () => {
    const adapter = await import('./amneziawg-adapter')
    expect([...adapter.AWG_INTEGER_FIELDS, ...adapter.AWG_RANGE_FIELDS, ...adapter.AWG_BOOLEAN_FIELDS]).toEqual(expect.arrayContaining([
      'jc', 'jmin', 'jmax', 's1', 's2', 's3', 's4', 'h1', 'h2', 'h3', 'h4',
      'content_padding_addition', 'random_trailers', 'disable_cookies',
    ]))
  })
})
