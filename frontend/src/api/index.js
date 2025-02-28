import axios from 'axios';

const API_BASE_URL = 'http://localhost:5002/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// 响应拦截器
api.interceptors.response.use(
    response => response.data,
    error => {
        console.error('API Error:', error);
        return Promise.reject(error);
    }
);

// API 方法
export const getAlerts = async () => {
    try {
        const response = await api.get('/alerts');
        return response;
    } catch (error) {
        console.error('获取预警信息失败:', error);
        throw error;
    }
};

export const getMarketData = async () => {
    try {
        const response = await api.get('/market-data');
        return response.data;
    } catch (error) {
        console.error('获取市场数据失败:', error);
        throw error;
    }
};

export const getChartData = async (symbol) => {
    try {
        const response = await api.get(`/chart-data/${symbol}`);
        return response;
    } catch (error) {
        console.error(`Failed to fetch chart data for ${symbol}:`, error);
        throw error;
    }
};

export default api; 