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

export async function* streamQuestion(question, signal) {
  const res = await fetch('/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
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
      if (line.startsWith('data: ')) {
        yield line.slice(6)
      }
    }
  }
}

export async function getEvalResults() {
  const res = await fetch('/evaluation/results')
  if (!res.ok) throw new Error('评估结果不存在')
  return res.json()
}

export async function getDatasetInfo() {
  const res = await fetch('/evaluation/dataset')
  if (!res.ok) throw new Error('测试集不存在')
  return res.json()
}
