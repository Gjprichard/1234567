<template>
  <div class="candlestick-chart">
    <div ref="chart" style="height: 600px;"></div>
  </div>
</template>

<script>
import * as echarts from 'echarts';

export default {
  name: 'CandlestickChart',
  props: {
    data: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      chart: null
    };
  },
  mounted() {
    this.initChart();
  },
  methods: {
    initChart() {
      this.chart = echarts.init(this.$refs.chart);
      this.updateChart();
    },
    updateChart() {
      const option = {
        grid: {
          left: '10%',
          right: '10%',
          bottom: '15%'
        },
        xAxis: {
          type: 'category',
          data: this.data.map(item => item.timestamp),
          axisLine: { lineStyle: { color: '#333' } }
        },
        yAxis: {
          type: 'value',
          scale: true,
          axisLine: { lineStyle: { color: '#333' } },
          splitLine: { lineStyle: { color: '#1a1a1a' } }
        },
        series: [
          {
            type: 'candlestick',
            data: this.data.map(item => [
              item.open,
              item.close,
              item.low,
              item.high
            ]),
            itemStyle: {
              color: '#ff5252',
              color0: '#00c853',
              borderColor: '#ff5252',
              borderColor0: '#00c853'
            }
          }
        ],
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        dataZoom: [
          {
            type: 'inside',
            start: 0,
            end: 100
          },
          {
            show: true,
            type: 'slider',
            bottom: '5%'
          }
        ]
      };
      
      this.chart.setOption(option);
    }
  },
  watch: {
    data: {
      handler() {
        this.updateChart();
      },
      deep: true
    }
  },
  beforeDestroy() {
    if (this.chart) {
      this.chart.dispose();
    }
  }
};
</script>

<style scoped>
.candlestick-chart {
  background: #121212;
  border-radius: 4px;
  padding: 20px;
  margin: 20px 0;
}
</style> 