import { describe, expect, it } from 'bun:test'
import { parseLogs, redactSensitiveLogMessage } from './logsUtils'

describe('AWG node log parsing', () => {
  it('classifies structured AWG logs without changing other logs', () => {
    const logs = parseLogs('[AWG] [info] event=start result=ok\n2026/09/18 01:02:03 xray worker ready [info]')
    expect(logs).toHaveLength(2)
    expect(logs[0]).toMatchObject({
      source: 'awg',
      type: 'info',
      message: 'event=start result=ok',
    })
    expect(logs[1].source).toBe('other')
    expect(logs[1].message).toContain('xray worker ready')
  })

  it('redacts high-risk secrets before a log reaches the UI', () => {
    const input =
      '[AWG] [error] event=uapi_error private_key=PRIVATESECRET psk=PSKSECRET HeaderProtectionKey=HEADERSECRET password=PASSSECRET api_key=APISECRET credential=CREDSECRET secret=GENERICSECRET Authorization: Bearer BEARERSECRET github_pat_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    const redacted = redactSensitiveLogMessage(input)
    for (const secret of ['PRIVATESECRET', 'PSKSECRET', 'HEADERSECRET', 'PASSSECRET', 'APISECRET', 'CREDSECRET', 'GENERICSECRET', 'BEARERSECRET', 'github_pat_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA']) {
      expect(redacted).not.toContain(secret)
    }
    expect(redacted.match(/\[REDACTED\]/g)?.length).toBeGreaterThanOrEqual(9)
  })

  it('redacts JSON-style secret fields before a log reaches the UI', () => {
    const input = '{"private_key":"JSONSECRET","api_key":"APIJSONSECRET","token":"TOKENJSONSECRET"}'
    const redacted = redactSensitiveLogMessage(input)
    for (const secret of ['JSONSECRET', 'APIJSONSECRET', 'TOKENJSONSECRET']) {
      expect(redacted).not.toContain(secret)
    }
  })

  it('keeps long AWG event messages intact after safe redaction', () => {
    const payload = 'x'.repeat(4096)
    const [log] = parseLogs(`[AWG] [warning] event=reconcile note=${payload}`)
    expect(log.source).toBe('awg')
    expect(log.type).toBe('warning')
    expect(log.message).toContain(payload)
  })
})
