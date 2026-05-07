'use client'

import { Toaster } from 'sonner'

/**
 * Client-only providers: kept lean so the RootLayout can stay a server
 * component. Wrap any future context providers (theme, swr config, etc.) here.
 */
export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster theme="dark" position="bottom-right" richColors />
    </>
  )
}
