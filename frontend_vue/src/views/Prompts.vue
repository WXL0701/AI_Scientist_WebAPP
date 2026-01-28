<template>
  <div>
    <div class="page-header">
      <h2>Prompt Sets</h2>
      <el-button type="primary" @click="showCreateSetDialog">Create Prompt Set</el-button>
    </div>

    <el-table :data="promptSets" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="created_at" label="Created At">
        <template #default="scope">
          {{ new Date(scope.row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="200">
        <template #default="scope">
          <el-button size="small" @click="handleManageVersions(scope.row)">Manage Versions</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Prompt Set Dialog -->
    <el-dialog v-model="createSetVisible" title="Create Prompt Set" width="30%">
      <el-form :model="createSetForm">
        <el-form-item label="Name">
          <el-input v-model="createSetForm.name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createSetVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleCreateSet">Create</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import client from '../api/client'

interface PromptSet {
  id: number
  name: string
  created_at: string
}

const router = useRouter()
const loading = ref(false)
const promptSets = ref<PromptSet[]>([])
const createSetVisible = ref(false)
const createSetForm = reactive({ name: '' })

const fetchPromptSets = async () => {
  loading.value = true
  try {
    const res = await client.get('/promptsets')
    promptSets.value = res.data
  } catch (error) {
    ElMessage.error('Failed to fetch prompt sets')
  } finally {
    loading.value = false
  }
}

const showCreateSetDialog = () => {
  createSetForm.name = ''
  createSetVisible.value = true
}

const handleCreateSet = async () => {
  try {
    const res = await client.post('/promptsets', createSetForm)
    ElMessage.success('Prompt set created')
    createSetVisible.value = false
    // Immediately navigate to the new detail page
    if (res.data && res.data.id) {
      router.push(`/prompts/${res.data.id}`)
    } else {
      fetchPromptSets()
    }
  } catch (error) {
    ElMessage.error('Failed to create prompt set')
  }
}

const handleManageVersions = (row: PromptSet) => {
  router.push(`/prompts/${row.id}`)
}

onMounted(() => {
  fetchPromptSets()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
