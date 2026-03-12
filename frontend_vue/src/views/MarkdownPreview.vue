<template>
  <div v-loading="loading">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="handleBack">Back</el-button>
        <h2 class="ml-2">{{ title }}</h2>
      </div>
      <div>
        <el-button :disabled="!path" @click="handleDownload">Download</el-button>
      </div>
    </div>

    <el-card v-if="path">
      <div class="markdown-body" v-html="renderedHtml"></div>
    </el-card>
    <el-empty v-else description="No file selected" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import markdownItKatex from '@vscode/markdown-it-katex'
import hljs from 'highlight.js'
import 'github-markdown-css/github-markdown-light.css'
import 'highlight.js/styles/github.css'
import 'katex/dist/katex.min.css'
import client from '../api/client'

const route = useRoute()
const router = useRouter()

const runId = computed(() => route.params.id as string)
const path = computed(() => (route.query.path as string) || '')

const loading = ref(false)
const markdownText = ref('')

const title = computed(() => {
  if (!path.value) return 'Markdown Preview'
  const filename = path.value.split('/').pop()
  return filename || 'Markdown Preview'
})

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: (code: string, language: string) => {
    if (language && hljs.getLanguage(language)) {
      return hljs.highlight(code, { language }).value
    }
    return hljs.highlightAuto(code).value
  }
})

md.use(markdownItKatex, { throwOnError: false })

const renderedHtml = computed(() => md.render(markdownText.value || ''))

const fetchMarkdown = async () => {
  if (!path.value) return
  loading.value = true
  try {
    const res = await client.get(`/runs/${runId.value}/download`, {
      params: { path: path.value },
      responseType: 'text'
    })
    markdownText.value = res.data
  } catch (e) {
    markdownText.value = ''
    ElMessage.error('Failed to load file')
  } finally {
    loading.value = false
  }
}

const handleDownload = async () => {
  if (!path.value) return
  try {
    const res = await client.get(`/runs/${runId.value}/download`, {
      params: { path: path.value },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', path.value.split('/').pop() || 'download')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (e) {
    ElMessage.error('Download failed')
  }
}

const handleBack = () => {
  router.push({ name: 'RunDetail', params: { id: runId.value } })
}

watchEffect(() => {
  if (!path.value) return
  fetchMarkdown()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-left {
  display: flex;
  align-items: center;
}
.ml-2 {
  margin-left: 10px;
}
.page-header h2 {
  color: #111111;
}
.markdown-body {
  padding: 12px;
  background: #ffffff;
  color: #111111;
}
</style>
