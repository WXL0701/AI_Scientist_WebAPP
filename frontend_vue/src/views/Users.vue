<template>
  <div>
    <div class="page-header">
      <h2>User Management</h2>
      <el-button type="primary" @click="showCreateDialog">Create User</el-button>
    </div>

    <el-table :data="users" style="width: 100%" v-loading="loading">
      <el-table-column prop="username" label="Username" />
      <el-table-column prop="role" label="Role" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'info'">
            {{ scope.row.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created At">
        <template #default="scope">
          {{ new Date(scope.row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createVisible" title="Create User" width="30%">
      <el-form :model="createForm" label-position="top">
        <el-form-item label="Username">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="Password">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="Role">
          <el-select v-model="createForm.role" style="width: 100%">
            <el-option label="user" value="user" />
            <el-option label="admin" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createVisible = false">Cancel</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreate">Create</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

interface UserItem {
  id: number
  username: string
  role: string
  created_at: string
}

const users = ref<UserItem[]>([])
const loading = ref(false)
const createVisible = ref(false)
const creating = ref(false)
const createForm = reactive({
  username: '',
  password: '',
  role: 'user'
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await client.get('/admin/users')
    users.value = res.data
  } catch (error) {
    ElMessage.error('Failed to fetch users')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  createForm.username = ''
  createForm.password = ''
  createForm.role = 'user'
  createVisible.value = true
}

const handleCreate = async () => {
  if (!createForm.username.trim() || !createForm.password) {
    ElMessage.warning('Username and password are required')
    return
  }
  creating.value = true
  try {
    await client.post('/admin/users', createForm)
    ElMessage.success('User created')
    createVisible.value = false
    fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to create user')
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
h2 {
  color: #303133;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
