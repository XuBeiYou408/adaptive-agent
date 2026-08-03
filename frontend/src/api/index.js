export async function healthCheck() {
  const res = await fetch('/health')
  if (!res.ok) throw new Error('服务不可用')
  return res.json()
}

export async function askQuestion(question) {
  const res = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error('问答请求失败')
  return res.json()
}

export async function* streamQuestion(question, signal, sessionId = 'default_session') {
  const cleanSessionId = String(sessionId).replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 64) || 'default_session'
  const res = await fetch('/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: cleanSessionId }),
    signal,
  })
  if (!res.ok) throw new Error('流式请求失败')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      const trimmedLine = line.trim()
      if (trimmedLine.startsWith('data: ')) {
        const rawData = trimmedLine.slice(6).trim()
        if (rawData === '[DONE]') continue
        try {
          const parsed = JSON.parse(rawData)
          yield parsed
        } catch {
          yield { type: 'content', content: rawData }
        }
      }
    }
  }
}

export async function getEvalResults() {
  const res = await fetch('/evaluation/results')
  if (!res.ok) throw new Error('评估结果不存在，请先运行评估')
  const json = await res.json()
  return json.data !== undefined ? json.data : json
}

export async function getDatasetInfo() {
  const res = await fetch('/evaluation/dataset')
  if (!res.ok) throw new Error('测试集不存在')
  const json = await res.json()
  return json.data !== undefined ? json.data : json
}
