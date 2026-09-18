import { describe, expect, it } from 'bun:test'
import { getAmneziaWGDownloadPayload, getAmneziaWGQrValue } from './subscription-config'

describe('native AmneziaWG modal payloads', () => {
  it('uses the exact native config for QR, copy, and download', () => {
    const config = '[Interface]\nPrivateKey = synthetic\nJc = 0\nRandomTrailers = off\n\n[Peer]\nEndpoint = 198.51.100.1:51820\n'
    expect(getAmneziaWGQrValue(config)).toBe(config)
    const download = getAmneziaWGDownloadPayload('synthetic.conf', config)
    expect(download.content).toBe(config)
    expect(download.fileName).toBe('synthetic.conf')
  })
})
