<template>
  <div class="market-monitor">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-left">
        <h2>市场监控系统</h2>
        <el-tag :type="isConnected ? 'success' : 'danger'" size="small">
          {{ isConnected ? '已连接' : '已断开' }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button 
            :icon="isDark ? 'el-icon-moon' : 'el-icon-sunny'"
            @click="toggleTheme"
          />
          <el-button 
            icon="el-icon-setting"
            @click="showSettings = true"
          />
        </el-button-group>
      </div>
    </el-header>

    <!-- 市场概览 -->
    <div class="market-overview" v-if="marketOverview">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card>
            <template #header>总成交量</template>
            <span class="overview-value">{{ marketOverview.totalVolume }}</span>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <template #header>平均价格</template>
            <span class="overview-value">{{ marketOverview.averagePrice }}</span>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <template #header>价格变化</template>
            <span :class="['overview-value', getChangeClass(marketOverview.priceChange)]">
              {{ marketOverview.priceChange }}
            </span>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <template #header>波动率</template>
            <span class="overview-value">{{ marketOverview.volatility }}</span>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 预警面板 -->
    <div class="alert-container">
      <AlertPanel />
    </div>

    <!-- 设置抽屉 -->
    <el-drawer
      v-model="showSettings"
      title="系统设置"
      size="400px"
    >
      <el-form :model="settings" label-width="120px">
        <el-form-item label="预警开关">
          <el-switch v-model="settings.alertEnabled" />
        </el-form-item>
        <el-form-item label="价格阈值">
          <el-input-number 
            v-model="settings.priceThreshold"
            :min="0.1"
            :max="10"
            :step="0.1"
          />
          <span class="unit">%</span>
        </el-form-item>
        <el-form-item label="成交量阈值">
          <el-input-number 
            v-model="settings.volumeThreshold"
            :min="1"
            :max="100"
            :step="1"
          />
          <span class="unit">%</span>
        </el-form-item>
        <el-form-item label="桌面通知">
          <el-switch v-model="settings.notificationEnabled" />
        </el-form-item>
        <el-form-item label="声音提醒">
          <el-switch v-model="settings.soundEnabled" />
        </el-form-item>
      </el-form>
    </el-drawer>

    <!-- 性能指标 -->
    <div v-if="import.meta.env.DEV" class="performance-metrics">
      <div class="metric">FPS: {{ fps }}</div>
      <div v-if="memory" class="metric">
        Memory: {{ memory.used }}MB / {{ memory.total }}MB
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { AlertPanel } from '@/components/AlertPanel'
import { useMarketData } from '@/composables/useMarketData'
import { useSettings } from '@/composables/useSettings'
import { useTheme } from '@/composables/useTheme'
import { usePerformance } from '@/composables/usePerformance'
import { formatters, getChangeClass } from '@/utils/formatters'

export default {
  name: 'MarketMonitor',
  components: {
    AlertPanel
  },
  setup() {
    const showSettings = ref(false)
    const { theme, isDark, toggleTheme } = useTheme()
    const { settings } = useSettings()
    const { fps, memory } = usePerformance()
    const { 
      marketData, 
      marketMetrics, 
      lastUpdate, 
      isConnected 
    } = useMarketData()

    // 市场概览数据
    const marketOverview = computed(() => {
      if (!marketMetrics.value) return null

      return {
        totalVolume: formatters.volume(marketMetrics.value.totalVolume),
        averagePrice: formatters.price(marketMetrics.value.averagePrice),
        priceChange: formatters.change(marketMetrics.value.priceChange),
        volatility: `${marketMetrics.value.volatility.toFixed(2)}%`
      }
    })

    return {
      showSettings,
      settings,
      theme,
      isDark,
      toggleTheme,
      marketOverview,
      isConnected,
      lastUpdate,
      fps,
      memory,
      getChangeClass
    }
  }
}
</script>

<style scoped>
.market-monitor {
  min-height: 100vh;
  background-color: var(--el-bg-color-page);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: var(--el-bg-color);
  box-shadow: var(--el-box-shadow-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.market-overview {
  padding: 20px;
}

.overview-value {
  font-size: 24px;
  font-weight: 600;
}

.alert-container {
  padding: 20px;
}

.unit {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
}

.performance-metrics {
  position: fixed;
  bottom: 20px;
  left: 20px;
  padding: 10px;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-light);
}

.metric {
  font-family: monospace;
  color: var(--el-text-color-secondary);
}

/* 变化指示器样式 */
.change-up {
  color: var(--el-color-success);
}

.change-down {
  color: var(--el-color-danger);
}

.change-critical {
  color: var(--el-color-danger);
  font-weight: bold;
}

.change-warning {
  color: var(--el-color-warning);
}
</style> 