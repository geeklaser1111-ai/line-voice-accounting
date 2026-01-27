/**
 * 工具函式
 */
const Utils = {
    /**
     * 格式化金額
     */
    formatMoney(amount) {
        return new Intl.NumberFormat('zh-TW', {
            style: 'currency',
            currency: 'TWD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    },

    /**
     * 格式化日期
     */
    formatDate(dateString, format = 'short') {
        const date = new Date(dateString);
        if (format === 'short') {
            return date.toLocaleDateString('zh-TW');
        }
        return date.toLocaleString('zh-TW');
    },

    /**
     * 取得今天日期（YYYY-MM-DD）
     */
    getToday() {
        return new Date().toISOString().split('T')[0];
    },

    /**
     * 取得本月第一天
     */
    getMonthStart() {
        const date = new Date();
        return new Date(date.getFullYear(), date.getMonth(), 1)
            .toISOString().split('T')[0];
    },

    /**
     * 取得本月最後一天
     */
    getMonthEnd() {
        const date = new Date();
        return new Date(date.getFullYear(), date.getMonth() + 1, 0)
            .toISOString().split('T')[0];
    },

    /**
     * 顯示 Toast 通知
     */
    showToast(message, type = 'success') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span>${type === 'success' ? '✓' : '✕'}</span>
            <span>${message}</span>
        `;

        container.appendChild(toast);

        // 自動移除
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /**
     * 顯示載入中
     */
    showLoading(container) {
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
            </div>
        `;
    },

    /**
     * 顯示空狀態
     */
    showEmpty(container, message = '暫無資料') {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
                <h3>${message}</h3>
                <p>開始記錄您的收支吧！</p>
            </div>
        `;
    },

    /**
     * 確認對話框
     */
    confirm(message) {
        return window.confirm(message);
    },

    /**
     * Debounce 函式
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * 生成圖表顏色
     */
    getChartColors(count) {
        const colors = [
            '#4A90D9', '#06C755', '#E74C3C', '#F39C12', '#9B59B6',
            '#1ABC9C', '#34495E', '#E91E63', '#00BCD4', '#FF5722',
            '#795548', '#607D8B', '#3F51B5', '#8BC34A', '#FFC107'
        ];
        return colors.slice(0, count);
    },

    /**
     * 預設分類
     */
    defaultCategories: {
        expense: ['餐飲', '交通', '購物', '娛樂', '日用品', '醫療', '教育', '其他'],
        income: ['薪資', '獎金', '投資', '兼職', '其他']
    },
};

// 導出
window.Utils = Utils;
