import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import Providers from '@/components/layout/Providers'
import AppShell from '@/components/layout/AppShell'
import ClassificationBanner from '@/components/layout/ClassificationBanner'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500', '600'],
})

export const metadata: Metadata = {
  title: 'Atalaya — OSINT Operations Center',
  description:
    'Atalaya: open-source intelligence platform for authorized investigations. Restricted access.',
  robots: { index: false, follow: false, nocache: true },
  referrer: 'no-referrer',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} bg-background text-gray-100 font-sans`}
      >
        <Providers>
          <div className="flex h-screen flex-col overflow-hidden">
            <ClassificationBanner position="top" />
            <AppShell>{children}</AppShell>
            <ClassificationBanner position="bottom" />
          </div>
        </Providers>
      </body>
    </html>
  )
}
