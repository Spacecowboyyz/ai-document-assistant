export function parseApiError(detail: unknown, fallback = 'Something went wrong'): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: string }).msg)
        }
        return fallback
      })
      .join('. ')
  }
  return fallback
}

export async function parseResponseError(
  response: Response,
  fallback = 'Request failed'
): Promise<string> {
  try {
    const body = await response.json()
    return parseApiError(body.detail, fallback)
  } catch {
    return fallback
  }
}
