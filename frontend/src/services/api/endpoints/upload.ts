const BASE = '/api'

export const uploadApi = {
  upload: (file: File, kind?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (kind) formData.append('kind', kind)
    return fetch(`${BASE}/uploads`, {
      method: 'POST',
      body: formData,
    }).then((res) => {
      if (!res.ok) throw new Error(`Upload ${res.status}: ${res.statusText}`)
      return res.json()
    }) as Promise<{ url: string; filename: string; size: number; content_type: string }>
  },
}
