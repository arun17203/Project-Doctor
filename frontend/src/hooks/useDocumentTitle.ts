import { useEffect } from 'react'

export function useDocumentTitle(title: string, subtitle?: string) {
  useEffect(() => {
    const fullTitle = subtitle ? `${title} — ${subtitle}` : title
    document.title = fullTitle
  }, [title, subtitle])
}
