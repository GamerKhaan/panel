import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PasswordInput } from '@/components/ui/password-input'
import { Textarea } from '@/components/ui/textarea'
import { useCoreEditorStore } from '@/features/core-editor/state/core-editor-store'
import { regenerateAmneziaWGKeys, syncAmneziaWGPublicKey } from '@/features/core-editor/kit/amneziawg-adapter'
import { RefreshCcw } from 'lucide-react'
import { toast } from 'sonner'

export function AmneziaWGForm() {
  const draft = useCoreEditorStore(s => s.awgDraft)
  const update = useCoreEditorStore(s => s.updateAwgDraft)
  if (!draft) return null

  const set = (key: 'interfaceName' | 'listenPort' | 'privateKey', value: string) =>
    update(d => syncAmneziaWGPublicKey({ ...d, [key]: value }))
  const regenerate = () => {
    try {
      update(regenerateAmneziaWGKeys)
      toast.success('New AmneziaWG keypair generated')
    } catch { toast.error('Could not generate AmneziaWG keypair') }
  }

  return <div className="space-y-8">
    <section className="grid grid-cols-1 gap-5 sm:grid-cols-2">
      <div className="space-y-2"><Label>Interface name</Label><Input dir="ltr" value={draft.interfaceName} onChange={e => set('interfaceName', e.target.value)} /></div>
      <div className="space-y-2"><Label>Listen port</Label><Input dir="ltr" inputMode="numeric" value={draft.listenPort} onChange={e => set('listenPort', e.target.value)} /></div>
      <div className="space-y-2"><Label>Private key</Label><div className="flex gap-2" dir="ltr"><PasswordInput value={draft.privateKey} onChange={e => set('privateKey', e.target.value)} /><Button type="button" size="icon" variant="ghost" onClick={regenerate} title="Regenerate keypair"><RefreshCcw className="h-4 w-4" /></Button></div></div>
      <div className="space-y-2"><Label>Public key</Label><Input dir="ltr" disabled value={draft.publicKey} /></div>
      <div className="space-y-2 sm:col-span-2"><Label>Pre-shared key (optional)</Label><PasswordInput dir="ltr" value={draft.preSharedKey} onChange={e => update(d => ({ ...d, preSharedKey: e.target.value, preSharedKeyKind: 'string' }))} /></div>
      <div className="space-y-2 sm:col-span-2"><Label>Interface addresses (one per line)</Label><Textarea dir="ltr" rows={3} value={draft.address.join('\n')} onChange={e => update(d => ({ ...d, address: e.target.value.split(/\r?\n/).map(v => v.trim()).filter(Boolean) }))} /></div>
    </section>
  </div>
}
