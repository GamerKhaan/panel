import { generateWireGuardKeyPair } from '@pasarguard/core-kit/wireguard'
import { getWireGuardPublicKey } from '@/utils/wireguard'

export const AWG_SCHEMA_VERSION = 1
export const AWG_IMPLEMENTATION = 'GamerKhaan/pasarguard-awg31-patch'

export type AwgValue = string | number | boolean

export interface AmneziaWGCoreDraft {
  schemaVersion: number
  implementation: string
  interfaceName: string
  listenPort: string
  privateKey: string
  publicKey: string
  preSharedKey: string
  preSharedKeyKind: 'absent' | 'null' | 'string'
  address: string[]
  awg: Record<string, AwgValue>
  extra: Record<string, unknown>
}

const known = new Set(['schema_version', 'implementation', 'interface_name', 'listen_port', 'private_key', 'public_key', 'pre_shared_key', 'address', 'awg'])

export const AWG_INTEGER_FIELDS = ['jc', 'jmin', 'jmax', 's1', 's2', 's3', 's4'] as const
export const AWG_RANGE_FIELDS = ['h1', 'h2', 'h3', 'h4', 'content_padding_addition', 'rekey_after_time', 'rekey_timeout', 'reject_after_time', 'keepalive_timeout', 'max_handshake_attempts'] as const
export const AWG_BOOLEAN_FIELDS = ['random_trailers', 'disable_cookies'] as const

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function createNewAmneziaWGDraft(): AmneziaWGCoreDraft {
  const pair = generateWireGuardKeyPair()
  return {
    schemaVersion: AWG_SCHEMA_VERSION,
    implementation: AWG_IMPLEMENTATION,
    interfaceName: 'awg0',
    listenPort: '51820',
    privateKey: pair.privateKey,
    publicKey: pair.publicKey,
    preSharedKey: '',
    preSharedKeyKind: 'absent',
    address: ['10.70.0.1/24'],
    awg: {
      jc: 0, jmin: 0, jmax: 0, s1: 16, s2: 20, s3: 12, s4: 24,
      h1: '10001-10010', h2: '20001-20010', h3: '30001-30010', h4: '40001-40010',
      content_padding_addition: '0-16', random_trailers: false, disable_cookies: false,
    },
    extra: {},
  }
}

export function amneziaWGConfigToDraft(raw: unknown): { ok: true; draft: AmneziaWGCoreDraft } | { ok: false; message: string } {
  if (!isObject(raw)) return { ok: false, message: 'AmneziaWG configuration must be an object' }
  if (raw.schema_version !== AWG_SCHEMA_VERSION) return { ok: false, message: `Unsupported AmneziaWG schema_version; expected ${AWG_SCHEMA_VERSION}` }
  if (raw.implementation !== AWG_IMPLEMENTATION) return { ok: false, message: `Unsupported AmneziaWG implementation; expected ${AWG_IMPLEMENTATION}` }
  if (!isObject(raw.awg)) return { ok: false, message: 'AmneziaWG awg must be an object' }
  const extra: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(raw)) if (!known.has(key)) extra[key] = value
  const privateKey = typeof raw.private_key === 'string' ? raw.private_key : ''
  const hasPreSharedKey = Object.prototype.hasOwnProperty.call(raw, 'pre_shared_key')
  let publicKey = typeof raw.public_key === 'string' ? raw.public_key : ''
  try { if (privateKey) publicKey = getWireGuardPublicKey(privateKey) } catch { /* server validation reports malformed keys */ }
  return {
    ok: true,
    draft: {
      schemaVersion: AWG_SCHEMA_VERSION,
      implementation: AWG_IMPLEMENTATION,
      interfaceName: typeof raw.interface_name === 'string' ? raw.interface_name : '',
      listenPort: String(raw.listen_port ?? ''),
      privateKey,
      publicKey,
      preSharedKey: typeof raw.pre_shared_key === 'string' ? raw.pre_shared_key : '',
      preSharedKeyKind: !hasPreSharedKey ? 'absent' : raw.pre_shared_key === null ? 'null' : 'string',
      address: Array.isArray(raw.address) ? raw.address.map(String) : [],
      awg: { ...(raw.awg as Record<string, AwgValue>) },
      extra,
    },
  }
}

export function amneziaWGDraftToConfig(draft: AmneziaWGCoreDraft): Record<string, unknown> {
  const listenPort = Number(draft.listenPort)
  const config: Record<string, unknown> = {
    ...draft.extra,
    schema_version: draft.schemaVersion,
    implementation: draft.implementation,
    interface_name: draft.interfaceName,
    private_key: draft.privateKey,
    public_key: draft.publicKey,
    listen_port: Number.isInteger(listenPort) ? listenPort : draft.listenPort,
    address: [...draft.address],
    awg: { ...draft.awg },
  }
  if (draft.preSharedKeyKind === 'string') config.pre_shared_key = draft.preSharedKey
  else if (draft.preSharedKeyKind === 'null') config.pre_shared_key = null
  else delete config.pre_shared_key
  return config
}

export function syncAmneziaWGPublicKey(draft: AmneziaWGCoreDraft): AmneziaWGCoreDraft {
  try {
    return { ...draft, publicKey: draft.privateKey ? getWireGuardPublicKey(draft.privateKey) : '' }
  } catch {
    return { ...draft, publicKey: '' }
  }
}

export function regenerateAmneziaWGKeys(draft: AmneziaWGCoreDraft): AmneziaWGCoreDraft {
  const pair = generateWireGuardKeyPair()
  return { ...draft, privateKey: pair.privateKey, publicKey: pair.publicKey }
}
