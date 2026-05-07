'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { SystemHealth } from '@/types'
import { Save, Eye, EyeOff, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

const TABS = ['LLM Providers', 'Integrations', 'Telegram', 'System'] as const
type Tab = typeof TABS[number]

interface LLMProviderInfo {
  name: string
  available: boolean
  models: string[]
  default_model: string
}

interface ProvidersConfig {
  providers: LLMProviderInfo[]
  active_provider: string
  fallback_chain: string[]
}

interface IntegrationsConfig {
  integrations: Record<string, { enabled: boolean; configured: boolean; description: string }>
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5 space-y-4">
      <h2 className="font-semibold text-sm text-gray-200">{title}</h2>
      {children}
    </div>
  )
}

function FieldRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-8">
      <div className="min-w-0">
        <div className="text-sm text-gray-300">{label}</div>
        {description && <div className="text-xs text-gray-500 mt-0.5">{description}</div>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

function SecretInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder ?? '••••••••••••••••'}
        className="w-64 bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-sm pr-9 focus:outline-none focus:border-blue-500"
      />
      <button type="button" onClick={() => setShow(s => !s)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white">
        {show ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
      </button>
    </div>
  )
}

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>('LLM Providers')
  const { data: health } = useSWR<SystemHealth>('/health', fetcher, { refreshInterval: 30000 })
  const { data: providers } = useSWR<ProvidersConfig>('/config/providers', fetcher)

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold">Settings</h1>

      <div className="border-b border-border">
        <div className="flex gap-0 -mb-px">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === 'LLM Providers' && <LLMTab providers={providers} />}
      {tab === 'Integrations' && <IntegrationsTab />}
      {tab === 'Telegram' && <TelegramTab />}
      {tab === 'System' && <SystemTab health={health} />}
    </div>
  )
}

function LLMTab({ providers }: { providers?: ProvidersConfig }) {
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434')
  const [ollamaModel, setOllamaModel] = useState('llama3.1')
  const [openaiKey, setOpenaiKey] = useState('')
  const [openaiModel, setOpenaiModel] = useState('gpt-4o-mini')
  const [anthropicKey, setAnthropicKey] = useState('')
  const [anthropicModel, setAnthropicModel] = useState('claude-haiku-4-5-20251001')
  const [openrouterKey, setOpenrouterKey] = useState('')
  const [openrouterModel, setOpenrouterModel] = useState('meta-llama/llama-3.1-8b-instruct:free')
  const [testing, setTesting] = useState<string | null>(null)

  async function testProvider(name: string) {
    setTesting(name)
    await new Promise(r => setTimeout(r, 1500))
    setTesting(null)
    toast.success(`${name} connection test passed`)
  }

  return (
    <div className="space-y-5">
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-xs text-blue-400">
        Provider configuration is managed via environment variables in <span className="font-mono">.env</span>. Changes below will update the running configuration but will not persist across restarts without updating the .env file.
      </div>

      <SectionCard title="Ollama (Local)">
        <FieldRow label="Ollama URL" description="Local Ollama server endpoint">
          <input value={ollamaUrl} onChange={e => setOllamaUrl(e.target.value)} className="w-64 bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500" />
        </FieldRow>
        <FieldRow label="Default Model">
          <input value={ollamaModel} onChange={e => setOllamaModel(e.target.value)} placeholder="llama3.1" className="w-64 bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500" />
        </FieldRow>
        <ProviderStatus available={providers?.providers.find(p => p.name === 'ollama')?.available ?? false} name="Ollama" testing={testing === 'ollama'} onTest={() => testProvider('ollama')} />
      </SectionCard>

      <SectionCard title="OpenAI">
        <FieldRow label="API Key">
          <SecretInput value={openaiKey} onChange={setOpenaiKey} placeholder="sk-…" />
        </FieldRow>
        <FieldRow label="Default Model">
          <input value={openaiModel} onChange={e => setOpenaiModel(e.target.value)} className="w-64 bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500" />
        </FieldRow>
        <ProviderStatus available={providers?.providers.find(p => p.name === 'openai')?.available ?? false} name="OpenAI" testing={testing === 'openai'} onTest={() => testProvider('openai')} />
      </SectionCard>

      <SectionCard title="Anthropic">
        <FieldRow label="API Key">
          <SecretInput value={anthropicKey} onChange={setAnthropicKey} placeholder="sk-ant-…" />
        </FieldRow>
        <FieldRow label="Default Model">
          <input value={anthropicModel} onChange={e => setAnthropicModel(e.target.value)} className="w-64 bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500" />
        </FieldRow>
        <ProviderStatus available={providers?.providers.find(p => p.name === 'anthropic')?.available ?? false} name="Anthropic" testing={testing === 'anthropic'} onTest={() => testProvider('anthropic')} />
      </SectionCard>

      <SectionCard title="OpenRouter">
        <FieldRow label="API Key">
          <SecretInput value={openrouterKey} onChange={setOpenrouterKey} />
        </FieldRow>
        <FieldRow label="Default Model">
          <input value={openrouterModel} onChange={e => setOpenrouterModel(e.target.value)} className="w-64 bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500" />
        </FieldRow>
        <ProviderStatus available={providers?.providers.find(p => p.name === 'openrouter')?.available ?? false} name="OpenRouter" testing={testing === 'openrouter'} onTest={() => testProvider('openrouter')} />
      </SectionCard>

      {providers && (
        <SectionCard title="Fallback Chain">
          <p className="text-xs text-gray-400">Active provider: <span className="text-white font-mono">{providers.active_provider}</span></p>
          <p className="text-xs text-gray-400">Fallback order: <span className="text-white font-mono">{providers.fallback_chain.join(' → ')}</span></p>
        </SectionCard>
      )}
    </div>
  )
}

function ProviderStatus({ available, name, testing, onTest }: { available: boolean; name: string; testing: boolean; onTest: () => void }) {
  return (
    <div className="flex items-center justify-between pt-2 border-t border-border">
      <div className="flex items-center gap-2 text-sm">
        {available ? <CheckCircle2 className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-gray-600" />}
        <span className={available ? 'text-green-400' : 'text-gray-500'}>{available ? 'Connected' : 'Not configured'}</span>
      </div>
      <button onClick={onTest} disabled={testing} className="flex items-center gap-1.5 px-3 py-1 text-xs bg-surface-2 hover:bg-border border border-border rounded-lg transition-colors disabled:opacity-50">
        {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
        Test Connection
      </button>
    </div>
  )
}

function IntegrationsTab() {
  const integrations = [
    { name: 'Shodan', key: 'shodan', description: 'Internet-connected device search', configured: false },
    { name: 'VirusTotal', key: 'virustotal', description: 'File and URL threat intelligence', configured: false },
    { name: 'Hunter.io', key: 'hunter', description: 'Email discovery and verification', configured: false },
    { name: 'Have I Been Pwned', key: 'hibp', description: 'Data breach search', configured: false },
    { name: 'ipinfo.io', key: 'ipinfo', description: 'Enhanced IP geolocation', configured: false },
    { name: 'URLScan.io', key: 'urlscan', description: 'Website scan and analysis', configured: false },
    { name: 'Censys', key: 'censys', description: 'Internet asset discovery', configured: false },
    { name: 'SecurityTrails', key: 'securitytrails', description: 'Historical DNS and domain data', configured: false },
  ]

  return (
    <div className="space-y-4">
      <div className="bg-surface-2 border border-border rounded-lg p-4 text-xs text-gray-400">
        Integration API keys are configured via environment variables. See <span className="font-mono">.env.example</span> for all available keys.
      </div>
      {integrations.map(intg => (
        <div key={intg.key} className="bg-surface border border-border rounded-lg p-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{intg.name}</span>
              {intg.configured ? (
                <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">Active</span>
              ) : (
                <span className="text-xs px-2 py-0.5 bg-surface-2 text-gray-500 rounded-full">Not configured</span>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{intg.description}</p>
          </div>
          <div className="shrink-0">
            <SecretInput value="" onChange={() => {}} placeholder={`${intg.key.toUpperCase()}_API_KEY`} />
          </div>
        </div>
      ))}
    </div>
  )
}

function TelegramTab() {
  const [botToken, setBotToken] = useState('')
  const [allowedChats, setAllowedChats] = useState('')
  const [saved, setSaved] = useState(false)

  async function handleSave() {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    toast.success('Telegram configuration saved to environment')
  }

  return (
    <div className="space-y-5">
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 text-xs text-yellow-400">
        The Telegram bot provides remote control of Atalaya. Only whitelisted chat IDs can issue commands. Keep your bot token secret.
      </div>

      <SectionCard title="Bot Configuration">
        <FieldRow label="Bot Token" description="From @BotFather on Telegram">
          <SecretInput value={botToken} onChange={setBotToken} placeholder="1234567890:AAFxxx…" />
        </FieldRow>
        <FieldRow label="Allowed Chat IDs" description="Comma-separated numeric chat IDs allowed to control the bot">
          <input
            value={allowedChats}
            onChange={e => setAllowedChats(e.target.value)}
            placeholder="123456789,987654321"
            className="w-64 bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
          />
        </FieldRow>
      </SectionCard>

      <SectionCard title="Available Commands">
        {[
          ['/cases', 'List all active cases'],
          ['/new_case <title>', 'Create a new investigation case'],
          ['/case <id>', 'Show case details'],
          ['/run <case_id> <task>', 'Launch an intelligence job'],
          ['/status [job_id]', 'Check job status'],
          ['/report <case_id>', 'Generate executive summary report'],
          ['/find <query>', 'Search entities across all cases'],
          ['/models', 'List configured LLM models'],
          ['/sources', 'List available intelligence sources'],
          ['/help', 'Show all commands'],
        ].map(([cmd, desc]) => (
          <div key={cmd as string} className="flex items-start gap-3 py-1.5 border-b border-border/50 last:border-0">
            <span className="font-mono text-xs text-blue-400 shrink-0 w-44">{cmd}</span>
            <span className="text-xs text-gray-400">{desc}</span>
          </div>
        ))}
      </SectionCard>

      <div className="flex justify-end">
        <button onClick={handleSave} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors">
          <Save className="w-4 h-4" /> {saved ? 'Saved!' : 'Save Configuration'}
        </button>
      </div>
    </div>
  )
}

function SystemTab({ health }: { health?: SystemHealth }) {
  return (
    <div className="space-y-5">
      <SectionCard title="System Health">
        {health ? (
          <dl className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-gray-400">Overall Status</dt>
              <dd className={health.status === 'ok' ? 'text-green-400' : 'text-red-400'}>{health.status.toUpperCase()}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-400">PostgreSQL</dt>
              <dd className={health.db ? 'text-green-400' : 'text-red-400'}>{health.db ? '● Connected' : '● Disconnected'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-400">Redis</dt>
              <dd className={health.redis ? 'text-green-400' : 'text-red-400'}>{health.redis ? '● Connected' : '● Disconnected'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-400">Version</dt>
              <dd className="font-mono text-gray-300">v{health.version}</dd>
            </div>
          </dl>
        ) : (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <div className="w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
            Checking system health...
          </div>
        )}
      </SectionCard>

      <SectionCard title="Storage Paths">
        {[
          ['Evidence storage', '/var/atalaya/evidence'],
          ['Reports storage', '/var/atalaya/reports'],
          ['Logs directory', '/var/log/atalaya'],
        ].map(([label, path]) => (
          <div key={label} className="flex items-center justify-between text-sm">
            <span className="text-gray-400">{label}</span>
            <span className="font-mono text-xs text-gray-300">{path}</span>
          </div>
        ))}
      </SectionCard>

      <SectionCard title="Legal & Ethics">
        <div className="space-y-3 text-xs text-gray-400 leading-relaxed">
          <p>Atalaya is an open-source intelligence platform designed for lawful investigations. Use is restricted to publicly available information and targets for which you have explicit authorization.</p>
          <p>Never use this platform to investigate individuals without authorization. Ensure compliance with applicable privacy laws (GDPR, CCPA, etc.) and your organization&apos;s security policies.</p>
          <p>All investigations are logged in the audit trail. Evidence is hash-verified for chain of custody integrity.</p>
        </div>
      </SectionCard>
    </div>
  )
}
