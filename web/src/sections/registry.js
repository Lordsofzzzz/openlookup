import DnsSection from './DnsSection.vue'
import DnssecSection from './DnssecSection.vue'
import EmailSecuritySection from './EmailSecuritySection.vue'
import ExposureSection from './ExposureSection.vue'
import IpSection from './IpSection.vue'
import RdapSection from './RdapSection.vue'
import SubdomainsSection from './SubdomainsSection.vue'
import TrustScoreSection from './TrustScoreSection.vue'

export const lookupSectionRegistry = [
  {
    key: 'ip', title: 'Infrastructure', column: 'main', order: 10, module: IpSection,
    frameClass: 'section', headerTag: 'div', headerClass: 'section-heading', titleTag: 'h2',
    transition: true, showFetchedAt: true, retryLabel: 'Refresh section',
    message: section => section?.message || '',
  },
  {
    key: 'exposure', title: 'Exposure', column: 'main', order: 20, module: ExposureSection,
    frameClass: 'section', headerTag: 'div', headerClass: 'section-heading', titleTag: 'h2',
    transition: true, showFetchedAt: true, retryLabel: 'Refresh section',
    message: section => section?.message || '',
  },
  {
    key: 'dns', title: 'DNS record set', column: 'main', order: 30, module: DnsSection,
    frameClass: 'section', headerTag: 'div', headerClass: 'section-heading', titleTag: 'h2',
    transition: true, showFetchedAt: true, retryLabel: 'Refresh section',
    message: section => section?.message || '',
  },
  {
    key: 'trust_score', title: 'WebTrustScore', column: 'side', order: 10, module: TrustScoreSection,
    frameClass: 'side-section', headerTag: 'h2', headerClass: 'side-heading', titleTag: 'span',
    transition: false, showFetchedAt: false, retryLabel: 'Check for updated report',
    message: section => section?.status === 'ok' || !section?.message ? '' : 'WebTrustScore is temporarily unavailable.',
  },
  {
    key: 'dnssec', title: 'DNSSEC', column: 'side', order: 20, module: DnssecSection,
    frameClass: 'side-section', headerTag: 'h2', headerClass: 'side-heading', titleTag: 'span',
    transition: false, showFetchedAt: true, retryLabel: 'Refresh section',
    message: section => section?.message || '',
  },
  {
    key: 'rdap', title: 'Registration profile', column: 'side', order: 30, module: RdapSection,
    frameClass: 'side-section', headerTag: 'h2', headerClass: 'side-heading', titleTag: 'span',
    transition: true, showFetchedAt: true, retryLabel: 'Refresh section',
    message: section => section?.message || '',
  },
  {
    key: 'email_security', title: 'Email security', column: 'side', order: 40, module: EmailSecuritySection,
    frameClass: 'side-section', headerTag: 'h2', headerClass: 'side-heading', titleTag: 'span',
    transition: true, showFetchedAt: true, retryLabel: 'Refresh section',
    message: section => section?.message || '',
  },
  {
    key: 'subdomains', title: 'Subdomains', column: 'side', order: 50, module: SubdomainsSection,
    frameClass: 'side-section', headerTag: 'h2', headerClass: 'side-heading', titleTag: 'span',
    transition: true, showFetchedAt: true, retryLabel: 'Refresh section',
    message: section => section?.message || '',
  },
]

export const lookupSectionNames = lookupSectionRegistry.map(section => section.key)
