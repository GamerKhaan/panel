import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useCoreEditorStore } from '@/features/core-editor/state/core-editor-store'
import { AWG_BOOLEAN_FIELDS, AWG_INTEGER_FIELDS, AWG_RANGE_FIELDS } from '@/features/core-editor/kit/amneziawg-adapter'

const title = (key: string) => key.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase())

export function AmneziaWGAdvancedForm() {
  const draft = useCoreEditorStore(s => s.awgDraft)
  const update = useCoreEditorStore(s => s.updateAwgDraft)
  if (!draft) return null

  const setAwg = (key: string, value: string | number | boolean) =>
    update(d => ({ ...d, awg: { ...d.awg, [key]: value } }))

  return <section className="space-y-4">
    <div>
      <h3 className="text-base font-semibold">AmneziaWG parameters</h3>
      <p className="text-sm text-muted-foreground">Protocol-specific values are validated by the server when the core is saved.</p>
    </div>
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {AWG_INTEGER_FIELDS.map(key => <div key={key} className="space-y-2"><Label>{title(key)}</Label><Input dir="ltr" inputMode="numeric" value={String(draft.awg[key] ?? '')} onChange={e => setAwg(key, e.target.value === '' ? '' : Number(e.target.value))} /></div>)}
      {AWG_RANGE_FIELDS.map(key => <div key={key} className="space-y-2"><Label>{title(key)}</Label><Input dir="ltr" value={String(draft.awg[key] ?? '')} onChange={e => setAwg(key, e.target.value)} /></div>)}
      {AWG_BOOLEAN_FIELDS.map(key => <div key={key} className="flex items-center justify-between gap-3 rounded-md border p-3"><Label>{title(key)}</Label><Switch checked={draft.awg[key] === true} onCheckedChange={value => setAwg(key, value)} /></div>)}
    </div>
  </section>
}
