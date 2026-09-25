<template>
  <section class="page" data-module="fault">
    <header class="page-head">
      <div>
        <h2>故障登记管理</h2>
        <p class="page-desc">维护设备故障，围绕故障编号、发生设备、故障现象、影响范围做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记设备故障</button>
        <button class="btn" type="button" @click="exportRows">导出故障登记清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <div class="grade-panel">
      <span class="grade-count">已选 {{ selectedIds.length }} 条</span>
      <label class="filter-item">
        <span>定级等级</span>
        <select v-model="grade">
          <option v-for="option in gradeOptions" :key="option" :value="option">
            {{ option }}（处理期限 {{ gradeDeadlineHint[option] }}）
          </option>
        </select>
      </label>
      <label class="filter-item grade-basis">
        <span>定级依据</span>
        <input v-model="basis" placeholder="填写本次统一套用的定级依据" />
      </label>
      <button class="btn primary" type="button" :disabled="grading" @click="submitGrade">
        {{ grading ? '定级中…' : '批量定级' }}
      </button>
      <span v-if="gradeMessage" class="muted-text">{{ gradeMessage }}</span>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>选择</th>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td>
            <input
              type="checkbox"
              :checked="selectedIds.includes(Number(row.id))"
              :disabled="!selectable(row)"
              :title="selectable(row) ? '勾选参与批量定级' : '已恢复或已挂起的故障不参与定级'"
              @change="toggleSelect(row)"
            />
          </td>
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无故障登记数据，可先登记设备故障</td>
        </tr>
      </tbody>
    </table>

    <div v-if="gradeResults.length" class="grade-results">
      <h3>本次定级结果</h3>
      <ul>
        <li v-for="item in gradeResults" :key="item.id" :class="item.ok ? 'ok-text' : 'error-text'">
          {{ item.message }}
        </li>
      </ul>
    </div>

    <div class="todo-section">
      <h3>处置待办（同一设备的故障已合并）</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>发生设备</th>
            <th>故障数量</th>
            <th>故障编号</th>
            <th>定级等级</th>
            <th>处理期限</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="todo in todos" :key="todo.发生设备">
            <td>{{ todo.发生设备 }}</td>
            <td>{{ todo.故障数量 }}</td>
            <td>{{ todo.故障编号.join('、') }}</td>
            <td>{{ todo.定级等级 }}</td>
            <td>{{ todo.处理期限 || '—' }}</td>
          </tr>
          <tr v-if="!todos.length">
            <td colspan="5" class="empty-state">暂无待处置故障</td>
          </tr>
        </tbody>
      </table>

      <h3>挂起故障（单独列出）</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>故障编号</th>
            <th>发生设备</th>
            <th>故障现象</th>
            <th>发生时间</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in suspended" :key="item.id">
            <td>{{ item.故障编号 }}</td>
            <td>{{ item.发生设备 }}</td>
            <td>{{ item.故障现象 || '—' }}</td>
            <td>{{ item.发生时间 }}</td>
            <td>{{ item.说明 }}</td>
          </tr>
          <tr v-if="!suspended.length">
            <td colspan="5" class="empty-state">暂无挂起故障</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条故障登记记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

interface GradeItem {
  id: number
  ok: boolean
  message: string
}

interface TodoGroup {
  发生设备: string
  故障编号: string[]
  故障数量: number
  定级等级: string
  处理期限: string
}

interface SuspendedItem {
  id: number
  故障编号: string
  发生设备: string
  故障现象: string | null
  发生时间: string
  说明: string
}

const ENDPOINT = '/api/fault'
const columns = ["故障编号", "发生设备", "故障现象", "影响范围", "发生时间", "报告人", "恢复时间", "故障状态", "定级等级", "处理期限"]
const actions = ["确认定级", "提交恢复", "挂起故障"]
const statuses = ["待定级", "已定级", "处置中", "已恢复", "已挂起"]
const stats = [{"label": "待定级故障", "value": 0}, {"label": "处置中故障", "value": 0}, {"label": "今日恢复数", "value": 0}]
const gradeOptions = ["事故", "障碍", "一般故障"]
const gradeDeadlineHint: Record<string, string> = { "事故": "1 天", "障碍": "2 天", "一般故障": "3 天" }

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const selectedIds = ref<number[]>([])
const grade = ref('一般故障')
const basis = ref('')
const grading = ref(false)
const gradeMessage = ref('')
const gradeResults = ref<GradeItem[]>([])
const todos = ref<TodoGroup[]>([])
const suspended = ref<SuspendedItem[]>([])

function selectable(row: Row) {
  return row.status !== '已恢复' && row.status !== '已挂起'
}

function toggleSelect(row: Row) {
  const id = Number(row.id)
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter(item => item !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '设备故障登记入口尚未接入审批流'
}

async function submitGrade() {
  gradeMessage.value = ''
  gradeResults.value = []
  if (!selectedIds.value.length) {
    gradeMessage.value = '请先勾选需要定级的故障'
    return
  }
  if (!basis.value.trim()) {
    gradeMessage.value = '请填写本次统一套用的定级依据'
    return
  }
  grading.value = true
  try {
    const response = await request(`${ENDPOINT}/grade`, {
      method: 'POST',
      body: JSON.stringify({ ids: selectedIds.value, grade: grade.value, basis: basis.value }),
    })
    const payload = await response.json()
    gradeMessage.value = payload.message ?? '批量定级已提交'
    gradeResults.value = payload.results ?? []
    if (payload.ok) {
      selectedIds.value = []
      await reload()
      await reloadTodos()
    }
  } catch (error) {
    gradeMessage.value = error instanceof Error ? error.message : '批量定级失败'
  } finally {
    grading.value = false
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      throw new Error('故障登记动作未生效，请稍后重试')
    }
    await reload()
    await reloadTodos()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '故障登记操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('设备故障列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '故障登记列表读取失败'
  }
}

async function reloadTodos() {
  try {
    const response = await request(`${ENDPOINT}/todos`)
    if (!response.ok) {
      throw new Error('处置待办读取失败')
    }
    const payload = await response.json()
    todos.value = payload.todos ?? []
    suspended.value = payload.suspended ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '处置待办读取失败'
  }
}

onMounted(() => {
  void reload()
  void reloadTodos()
})
</script>
