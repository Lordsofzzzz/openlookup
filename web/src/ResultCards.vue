<script setup>
import SectionFrame from './sections/SectionFrame.vue'
import { lookupSectionRegistry } from './sections/registry.js'

const props = defineProps({
  sections: { type: Object, required: true },
  retries: { type: Object, required: true },
  retryErrors: { type: Object, required: true },
  streamStatus: { type: String, required: true },
})
const emit = defineEmits(['retry'])

const mainSections = lookupSectionRegistry
  .filter(entry => entry.column === 'main')
  .sort((left, right) => left.order - right.order)
const sideSections = lookupSectionRegistry
  .filter(entry => entry.column === 'side')
  .sort((left, right) => left.order - right.order)

function retry(key) {
  emit('retry', key)
}
</script>

<template>
  <div class="layout">
    <div class="main-col">
      <SectionFrame
        v-for="entry in mainSections"
        :key="entry.key"
        :entry="entry"
        :section="props.sections[entry.key]"
        :stream-status="props.streamStatus"
        :retrying="!!props.retries[entry.key]"
        :retry-error="props.retryErrors[entry.key]"
        @retry="retry(entry.key)"
      >
        <component :is="entry.module" :section="props.sections[entry.key]" />
      </SectionFrame>
    </div>

    <aside class="side-col">
      <SectionFrame
        v-for="entry in sideSections"
        :key="entry.key"
        :entry="entry"
        :section="props.sections[entry.key]"
        :stream-status="props.streamStatus"
        :retrying="!!props.retries[entry.key]"
        :retry-error="props.retryErrors[entry.key]"
        @retry="retry(entry.key)"
      >
        <component :is="entry.module" :section="props.sections[entry.key]" />
      </SectionFrame>
    </aside>
  </div>
</template>
