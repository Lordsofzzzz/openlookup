<script setup>
import { computed } from 'vue'

import SectionRefreshButton from '../components/SectionRefreshButton.vue'
import { formatLookupDate } from '../utils/formatLookupDate.js'

const props = defineProps({
  entry: { type: Object, required: true },
  section: { type: Object, default: null },
  streamStatus: { type: String, required: true },
  retrying: Boolean,
  retryError: { type: String, default: '' },
})
const emit = defineEmits(['retry'])

const status = computed(() => props.section?.status ?? (props.streamStatus === 'loading' ? 'loading' : 'waiting'))
const pending = computed(() => status.value === 'loading' || props.retrying)
const message = computed(() => props.entry.message(props.section))
</script>

<template>
  <section :class="entry.frameClass">
    <component :is="entry.headerTag" :class="entry.headerClass">
      <component :is="entry.titleTag">{{ entry.title }}</component>
      <SectionRefreshButton
        :label="entry.retryLabel"
        :status="status"
        :pending="pending"
        :error="retryError"
        @retry="emit('retry')"
      />
    </component>
    <div v-if="message" class="note">{{ message }}</div>
    <Transition v-if="entry.transition" name="reveal">
      <div v-if="section?.status === 'ok'"><slot :section="section" /></div>
    </Transition>
    <div v-else-if="section?.status === 'ok'"><slot :section="section" /></div>
    <div v-if="entry.showFetchedAt && section" class="section-meta">{{ formatLookupDate(section.fetched_at) }}</div>
  </section>
</template>
