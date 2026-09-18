export type LogType = 'error' | 'warning' | 'info' | 'debug'
export type LogVariant = 'red' | 'yellow' | 'blue' | 'orange'
export type LogSource = 'awg' | 'other'

export interface LogLine {
  id: string
  rawTimestamp: string | null
  timestamp: Date | null
  type: LogType
  source: LogSource
  message: string
}

interface LogStyle {
  type: LogType
  variant: LogVariant
  color: string
}

const LOG_STYLES: Record<LogType, LogStyle> = {
  error: {
    type: 'error',
    variant: 'red',
    color: 'bg-red-500/40',
  },
  warning: {
    type: 'warning',
    variant: 'orange',
    color: 'bg-orange-500/40',
  },
  info: {
    type: 'info',
    variant: 'blue',
    color: 'bg-blue-600/40',
  },
  debug: {
    type: 'debug',
    variant: 'yellow',
    color: 'bg-yellow-500/40',
  },
} as const

let logSeq = 0

function nextLogId(): string {
  logSeq += 1
  return String(logSeq)
}

export function appendTrim<T>(prev: T[], next: T[], max: number): T[] {
  if (next.length === 0) return prev
  const total = prev.length + next.length
  if (total <= max) return prev.length === 0 ? next : prev.concat(next)
  return prev.concat(next).slice(-max)
}

export function redactSensitiveLogMessage(value: string): string {
  return value
    .replace(/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/gi, '[REDACTED]')
    .replace(/\bAuthorization\s*:\s*Bearer\s+[^\s,;]+/gi, 'Authorization: Bearer [REDACTED]')
    .replace(/\bgithub_pat_[A-Za-z0-9_]{20,}\b/g, '[REDACTED]')
    .replace(/\bgh[opusr]_[A-Za-z0-9]{20,}\b/g, '[REDACTED]')
    .replace(
      /(["']?)\b(private(?:[_ -]?key)?|preshared(?:[_ -]?key)?|pre[_ -]?shared[_ -]?key|header[_ -]?protection[_ -]?key|psk|password|passwd|api[_ -]?key|access[_ -]?token|github[_ -]?token|subscription[_ -]?token|credential|secret|token)\b\1(\s*[:=]\s*)(?:(["'])[^"']*\4|[^\s,;}]+)/gi,
      (_match, keyQuote: string, key: string, separator: string, valueQuote: string) =>
        `${keyQuote}${key}${keyQuote}${separator}${valueQuote ? `${valueQuote}[REDACTED]${valueQuote}` : '[REDACTED]'}`,
    )
}

export function getLogSource(message: string): LogSource {
  return /^\s*(?:\[(?:awg|amneziawg)\]|(?:awg|amneziawg)(?:[_\s:-]|$))/i.test(message) ? 'awg' : 'other'
}

export function parseLogs(logString: string): LogLine[] {
  // Regex to match the log line format
  // Example of return :
  // 1 2024-12-10T10:00:00.000Z The server is running on port 8080
  // Should return :
  // { timestamp: new Date("2024-12-10T10:00:00.000Z"),
  // message: "The server is running on port 8080" }
  const logRegex = /^(?:(\d+)\s+)?(\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} UTC)?\s*(.*)$/

  return redactSensitiveLogMessage(logString)
    .split('\n')
    .map(line => line.trim())
    .filter(line => line !== '')
    .map(line => {
      const match = line.match(logRegex)
      if (!match) return null

      const [, , timestamp, message] = match

      if (!message?.trim()) return null

      let parsedTimestamp: Date | null = null
      if (timestamp) {
        try {
          // Handle Xray format: 2025/09/27 13:26:58.279079 (assume UTC)
          if (timestamp.includes('/')) {
            parsedTimestamp = new Date(timestamp + 'Z') // Treat as UTC
          } else {
            // Handle other formats
            parsedTimestamp = new Date(timestamp.replace(' UTC', 'Z'))
          }
          // Validate the parsed date is valid
          if (isNaN(parsedTimestamp.getTime())) {
            parsedTimestamp = null
          }
        } catch {
          // If date parsing fails, set to null
          parsedTimestamp = null
        }
      }

      const source = getLogSource(message)
      const type = getLogType(message).type

      // Remove source/severity indicators from the text because they are rendered as badges.
      let cleanedMessage = message.trim()
      if (source === 'awg') {
        cleanedMessage = cleanedMessage.replace(/^\[(?:AWG|AMNEZIAWG)\]\s*/i, '')
        cleanedMessage = cleanedMessage.replace(/^(?:AWG|AMNEZIAWG)[_\s:-]+/i, '')
      }
      cleanedMessage = cleanedMessage.replace(/^\[(Debug|Info|Warn|Warning|Error)\]\s*/i, '')
      cleanedMessage = cleanedMessage.replace(/^(Debug|Info|Warn|Warning|Error):\s*/i, '')

      return {
        id: nextLogId(),
        rawTimestamp: timestamp ?? null,
        timestamp: parsedTimestamp,
        type,
        source,
        message: cleanedMessage,
      }
    })
    .filter(log => log !== null) as LogLine[]
}

// Detect log type based on Xray core message content
export const getLogType = (message: string): LogStyle => {
  if (/\[error\]/i.test(message)) {
    return LOG_STYLES.error
  }

  if (/^\s*(error|fatal)\b/i.test(message)) {
    return LOG_STYLES.error
  }

  if (/\[warning\]/i.test(message) || /\[warn\]/i.test(message)) {
    return LOG_STYLES.warning
  }

  if (/^\s*(warning|warn)\b/i.test(message)) {
    return LOG_STYLES.warning
  }

  if (/\[info\]/i.test(message)) {
    return LOG_STYLES.info
  }

  if (/^\s*info\b/i.test(message)) {
    return LOG_STYLES.info
  }

  if (/\[debug\]/i.test(message)) {
    return LOG_STYLES.debug
  }

  if (/^\s*debug\b/i.test(message)) {
    return LOG_STYLES.debug
  }

  // Xray access logs: "from IP:port accepted tcp/udp:destination:port [info] email: user@example.com"
  if (/from\s+.+:\d+\s+accepted\s+(tcp|udp):.+:\d+\s+\[.+\]\s+email:\s+.+/i.test(message)) {
    return LOG_STYLES.info
  }

  // Default to info
  return LOG_STYLES.info
}

export const getLogStyle = (type: LogType): LogStyle => LOG_STYLES[type]
