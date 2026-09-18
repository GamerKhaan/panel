import type { CoreKind } from '@pasarguard/core-kit'
import type { CoreResponseType } from '@/service/api'

export type PanelCoreKind = CoreKind | 'awg'

export function apiCoreTypeToKind(type: CoreResponseType | undefined): PanelCoreKind {
  if (type === 'gamerkhaan_amneziawg') return 'awg'
  if (type === 'wg') return 'wg'
  return 'xray'
}

export function isSupportedCoreEditorKind(type: CoreResponseType | undefined): boolean {
  return type === 'gamerkhaan_amneziawg' || type === 'wg' || type === 'xray' || type == null || type === undefined
}
