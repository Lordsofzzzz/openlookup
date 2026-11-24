import { z } from 'zod'

const strings = z.array(z.string())
const dnsRecord = z.object({ type: z.string(), value: z.string(), ttl: z.number() })
const emailPolicy = z.object({ status: z.string(), summary: z.string(), records: strings })
const host = z.object({
  ip: z.string(), found: z.boolean(), ports: z.array(z.number()),
  cpes: strings, hostnames: strings, tags: strings, vulns: strings,
})
const nullableText = z.string().nullable()
const dataSchemas = {
  dns: z.object({ records: z.array(dnsRecord) }),
  dnssec: z.object({ status: z.string(), summary: z.string() }),
  ip: z.object({
    addresses: strings,
    address_asns: z.array(z.object({
      ip: z.string(), asns: z.array(z.object({ asn: z.string(), name: nullableText })),
    })).optional(),
    networks: z.array(z.object({
      asn: z.string(), prefix: z.string(), country: z.string(), allocated: nullableText,
    })),
  }),
  rdap: z.object({
    registrar: nullableText, nameservers: strings, created: nullableText,
    updated: nullableText, expires: nullableText, status: strings,
  }),
  subdomains: z.object({ count: z.number(), truncated: z.boolean(), subdomains: strings }),
  exposure: z.object({ hosts: z.array(host), truncated: z.boolean().default(false), errors: strings.optional() }),
  email_security: z.object({
    spf: emailPolicy, dmarc: emailPolicy.extend({ policy: nullableText.optional() }),
    mta_sts: emailPolicy, tls_rpt: emailPolicy, errors: strings.optional(),
  }),
}

export type DnsRecord = z.infer<typeof dnsRecord>
export type SectionName = keyof typeof dataSchemas
export type Sections = {
  [K in SectionName]?: {
    section: K
    fetched_at: string
    message?: string | null
  } & (
    | { status: 'ok'; data: z.infer<(typeof dataSchemas)[K]> }
    | { status: 'error' | 'timeout'; data?: unknown }
  )
}

const envelope = z.object({
  fetched_at: z.string(), message: nullableText.optional(),
  status: z.enum(['ok', 'error', 'timeout']), data: z.unknown().optional(),
})

export function unreadable(section: SectionName) {
  return { section, status: 'error' as const, fetched_at: '', message: `Unreadable ${section.replace('_', ' ')} result.` }
}

export function decodeResult(input: unknown, expected?: SectionName) {
  const key = z.object({ section: z.string() }).safeParse(input)
  if (!key.success || !Object.hasOwn(dataSchemas, key.data.section)) return expected ? unreadable(expected) : null
  const section = key.data.section as SectionName
  if (expected && expected !== section) return unreadable(expected)
  const parsed = envelope.safeParse(input)
  if (!parsed.success) return unreadable(section)
  const result = parsed.data
  if (result.status !== 'ok') return { ...result, section }
  const data = dataSchemas[section].safeParse(result.data)
  return data.success ? { ...result, section, data: data.data } : unreadable(section)
}
