<template>
  <div class="alert-panel" :data-theme="theme">
    <div class="alert-header">
      <div class="header-left">
        <h3>市场预警</h3>
        <el-tag :type="alertEnabled ? 'success' : 'info'" size="small">
          {{ alertEnabled ? '监控中' : '已暂停' }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-tooltip content="开启/关闭预警" placement="top">
          <el-switch
            v-model="alertEnabled"
            active-color="#13ce66"
            inactive-color="#ff4949"
          />
        </el-tooltip>
      </div>
    </div>
    
    <div class="alert-settings" v-if="alertEnabled">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="价格阈值">
            <el-input-number 
              v-model="priceThreshold" 
              :min="0.1" 
              :max="10"
              :step="0.1"
              size="small"
            />
            <span class="threshold-unit">%</span>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="成交量阈值">
            <el-input-number 
              v-model="volumeThreshold" 
              :min="1" 
              :max="100"
              :step="1"
              size="small"
            />
            <span class="threshold-unit">%</span>
          </el-form-item>
        </el-col>
      </el-row>
    </div>

    <div v-if="alerts.length > 0" class="alert-content">
      <div class="alert-summary">
        <el-badge :value="alerts.length" :type="getAlertBadgeType()">
          <span class="summary-text">检测到 {{ alerts.length }} 个异常波动</span>
        </el-badge>
      </div>

      <el-scrollbar height="400px">
        <transition-group name="alert-list">
          <el-card
            v-for="alert in sortedAlerts"
            :key="alert.time + alert.symbol"
            class="alert-item"
            :class="getAlertClass(alert)"
          >
            <div class="alert-item-header">
              <span class="symbol">{{ alert.symbol }}/USDT</span>
              <span class="time">{{ formatTime(alert.time) }}</span>
            </div>
            
            <div class="alert-item-body">
              <div class="metric-row">
                <span class="label">价格:</span>
                <span class="value">{{ formatPrice(alert.price) }}</span>
                <span :class="['change', getChangeClass(alert.price_change, 'price')]">
                  {{ formatChange(alert.price_change) }}
                </span>
              </div>
              
              <div class="metric-row">
                <span class="label">成交量变化:</span>
                <span :class="['change', getChangeClass(alert.volume_change, 'volume')]">
                  {{ formatChange(alert.volume_change) }}
                </span>
              </div>
            </div>

            <div class="alert-severity" :class="alert.severity">
              {{ getSeverityText(alert.severity) }}
            </div>
          </el-card>
        </transition-group>
      </el-scrollbar>
    </div>
    
    <div v-else class="no-alerts">
      <el-empty 
        description="暂无预警信息" 
        :image-size="100"
      >
        <template #description>
          <p>当前市场波动正常</p>
          <p class="sub-text">将在检测到异常波动时通知您</p>
        </template>
      </el-empty>
    </div>

    <div v-if="loading" class="loading-overlay">
      <el-loading-spinner />
    </div>
    
    <div v-if="error" class="error-message">
      <el-alert
        :title="error.message"
        type="error"
        show-icon
        closable
        @close="error = null"
      />
    </div>

    <div class="theme-switch">
      <el-tooltip content="切换主题" placement="top">
        <el-button
          circle
          :icon="theme === 'dark' ? 'el-icon-moon' : 'el-icon-sunny'"
          @click="setTheme(theme === 'dark' ? 'light' : 'dark')"
        />
      </el-tooltip>
    </div>

    <el-drawer
      v-model="showSettings"
      title="预警设置"
      size="300px"
    >
      <el-form :model="settings" label-width="100px">
        <el-form-item label="通知提醒">
          <el-switch v-model="settings.notificationEnabled" />
        </el-form-item>
        <el-form-item label="声音提醒">
          <el-switch v-model="settings.soundEnabled" />
        </el-form-item>
      </el-form>
    </el-drawer>

    <!-- 添加性能指标显示 -->
    <div v-if="import.meta.env.DEV" class="performance-metrics">
      <div class="metric">FPS: {{ fps }}</div>
      <div v-if="memory" class="metric">
        Memory: {{ memory.used }}MB / {{ memory.total }}MB
      </div>
    </div>

    <!-- 添加市场概览 -->
    <div v-if="marketOverview" class="market-overview">
      <div class="overview-item">
        <div class="item-label">总成交量</div>
        <div class="item-value">{{ marketOverview.totalVolume }}</div>
      </div>
      <div class="overview-item">
        <div class="item-label">平均价格</div>
        <div class="item-value">{{ marketOverview.averagePrice }}</div>
      </div>
      <div class="overview-item">
        <div class="item-label">价格变化</div>
        <div class="item-value" :class="getChangeClass(marketOverview.priceChange)">
          {{ marketOverview.priceChange }}
        </div>
      </div>
      <div class="overview-item">
        <div class="item-label">波动率</div>
        <div class="item-value">{{ marketOverview.volatility }}</div>
      </div>
    </div>

    <!-- 添加连接状态指示器 -->
    <div class="connection-status" :class="{ connected: isConnected }">
      {{ isConnected ? '已连接' : '已断开' }}
    </div>
  </div>
</template>

<script>
import { useAlerts } from '@/composables/useAlerts'
import { useTheme } from '@/composables/useTheme'
import { useSettings } from '@/composables/useSettings'
import { useNotification } from '@/composables/useNotification'
import { usePerformance } from '@/composables/usePerformance'
import { formatters, getChangeClass, getSeverityText } from '@/utils/formatters'
import { useMarketData } from '@/composables/useMarketData'
import { computed } from 'vue'

export default {
  name: 'AlertPanel',
  setup() {
    const { theme, setTheme } = useTheme()
    const { settings } = useSettings()
    const { notificationEnabled, isSoundEnabled, notify } = useNotification({
      defaultEnabled: settings.value.notificationEnabled,
      soundEnabled: settings.value.soundEnabled
    })
    const { fps, memory } = usePerformance()

    const {
      alerts,
      sortedAlerts,
      alertEnabled,
      priceThreshold,
      volumeThreshold,
      criticalAlertsCount,
      warningAlertsCount,
      error,
      loading
    } = useAlerts({
      defaultEnabled: settings.value.alertEnabled,
      defaultPriceThreshold: settings.value.priceThreshold,
      defaultVolumeThreshold: settings.value.volumeThreshold,
      maxAlerts: settings.value.maxAlerts,
      checkInterval: settings.value.checkInterval,
      onNewAlert: (alert) => {
        notify({
          title: `${alert.symbol} ${getSeverityText(alert.severity)}`,
          message: `价格变化: ${formatters.change(alert.price_change)}`,
          type: alert.severity === 'critical' ? 'error' : 'warning'
        })
      }
    })

    const { 
      marketData, 
      marketMetrics, 
      lastUpdate, 
      isConnected 
    } = useMarketData()

    // 添加市场概览
    const marketOverview = computed(() => {
      if (!marketMetrics.value) return null

      return {
        totalVolume: formatters.volume(marketMetrics.value.totalVolume),
        averagePrice: formatters.price(marketMetrics.value.averagePrice),
        priceChange: formatters.change(marketMetrics.value.priceChange),
        volatility: `${marketMetrics.value.volatility.toFixed(2)}%`
      }
    })

    // 监听设置变化
    watch([alertEnabled, priceThreshold, volumeThreshold], ([enabled, price, volume]) => {
      settings.value = {
        ...settings.value,
        alertEnabled: enabled,
        priceThreshold: price,
        volumeThreshold: volume
      }
    })

    const getAlertClass = (alert) => {
      const priceChange = Math.abs(alert.price_change)
      const volumeChange = Math.abs(alert.volume_change)
      
      if (priceChange >= 5 || volumeChange >= 100) return 'alert-critical'
      if (priceChange >= 3 || volumeChange >= 50) return 'alert-warning'
      return 'alert-normal'
    }

    const getAlertBadgeType = () => {
      return criticalAlertsCount.value > 0 ? 'danger' : 'warning'
    }

    return {
      alerts,
      sortedAlerts,
      alertEnabled,
      priceThreshold,
      volumeThreshold,
      formatters,
      getChangeClass,
      getSeverityText,
      getAlertClass,
      getAlertBadgeType,
      criticalAlertsCount,
      warningAlertsCount,
      error,
      loading,
      theme,
      setTheme,
      settings,
      notificationEnabled,
      isSoundEnabled,
      fps,
      memory,
      marketOverview,
      lastUpdate,
      isConnected
    }
  }
}
</script>

<style scoped>
/* 优化样式变量 */
:root {
  --alert-transition: all 0.3s ease;
  --alert-shadow: 0 2px 12px rgba(0,0,0,0.1);
  --alert-hover-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.alert-panel {
  padding: 20px;
  background: var(--el-bg-color);
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left h3 {
  margin: 0;
  font-size: 18px;
  color: var(--el-text-color-primary);
}

.alert-settings {
  margin-bottom: 20px;
  padding: 15px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.threshold-unit {
  margin-left: 5px;
  color: var(--el-text-color-secondary);
}

.alert-content {
  margin-top: 20px;
}

.alert-summary {
  margin-bottom: 15px;
  text-align: center;
}

.summary-text {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

/* 优化动画效果 */
.alert-item {
  margin-bottom: 12px;
  border-radius: 8px;
  transition: var(--alert-transition);
  transform-origin: center;
  will-change: transform, box-shadow;
}

.alert-item:hover {
  transform: translateY(-2px) scale(1.01);
  box-shadow: var(--alert-hover-shadow);
}

.alert-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.symbol {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.value {
  font-family: monospace;
  font-size: 14px;
}

/* 优化变化指示器样式 */
.change {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  transition: var(--alert-transition);
}

.change-critical {
  background-color: var(--el-color-danger-light-8);
  color: var(--el-color-danger);
  font-weight: 600;
}

.change-warning {
  background-color: var(--el-color-warning-light-8);
  color: var(--el-color-warning);
}

.change.up {
  background-color: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.change.down {
  background-color: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.alert-severity {
  margin-top: 10px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  text-align: center;
}

.alert-severity.critical {
  background-color: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.alert-severity.warning {
  background-color: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
}

.alert-severity.normal {
  background-color: var(--el-color-info-light-9);
  color: var(--el-color-info);
}

.no-alerts {
  padding: 40px 20px;
  text-align: center;
}

.sub-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 5px;
}

/* 优化列表动画 */
.alert-list-move {
  transition: transform 0.5s ease;
}

.alert-list-enter-active {
  transition: all 0.5s ease-out;
}

.alert-list-leave-active {
  transition: all 0.5s ease-in;
  position: absolute;
}

.alert-list-enter-from,
.alert-list-leave-to {
  opacity: 0;
  transform: translateX(-30px) scale(0.9);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.error-message {
  margin: 10px 0;
}

.theme-switch {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 100;
}

.performance-metrics {
  position: fixed;
  bottom: 20px;
  left: 20px;
  z-index: 100;
  padding: 10px;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.metric {
  margin-bottom: 5px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.market-overview {
  margin-top: 20px;
  padding: 15px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.overview-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.item-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.item-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.connection-status {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 100;
  padding: 10px 20px;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
  text-align: center;
}

.connection-status.connected {
  background-color: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.connection-status.disconnected {
  background-color: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}
</style> 