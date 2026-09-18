import { AmneziaWGForm } from './amneziawg-form'
import { AmneziaWGAdvancedForm } from './amneziawg-advanced-form'
import { useCoreEditorStore } from '@/features/core-editor/state/core-editor-store'

export function AmneziaWGCoreEditor() {
  const section = useCoreEditorStore(s => s.activeSection)
  return section === 'advanced'
    ? <AmneziaWGAdvancedForm />
    : <AmneziaWGForm />
}
