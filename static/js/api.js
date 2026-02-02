/**
 * API 封裝模組
 */
const API = {
    /**
     * 發送 API 請求
     */
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
        };

        const response = await fetch(url, { ...defaultOptions, ...options });

        // 處理未授權（只在非登入頁時重定向）
        if (response.status === 401) {
            if (!window.location.pathname.includes('index.html')) {
                window.location.href = '/static/index.html';
            }
            throw new Error('未登入');
        }

        // 處理其他錯誤
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '請求失敗' }));
            throw new Error(error.detail || '請求失敗');
        }

        // 檢查是否有內容
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        }

        return response;
    },

    /**
     * GET 請求
     */
    get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return this.request(fullUrl);
    },

    /**
     * POST 請求
     */
    post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * PUT 請求
     */
    put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    /**
     * DELETE 請求
     */
    delete(url) {
        return this.request(url, {
            method: 'DELETE',
        });
    },

    // ============ 認證 API ============

    /**
     * 取得當前用戶
     */
    getCurrentUser() {
        return this.get('/auth/me');
    },

    /**
     * 登出
     */
    logout() {
        return this.post('/auth/logout');
    },

    // ============ 交易 API ============

    /**
     * 取得交易列表
     */
    getTransactions(params = {}) {
        return this.get('/api/transactions', params);
    },

    /**
     * 取得單筆交易
     */
    getTransaction(id) {
        return this.get(`/api/transactions/${id}`);
    },

    /**
     * 新增交易
     */
    createTransaction(data) {
        return this.post('/api/transactions', data);
    },

    /**
     * 更新交易
     */
    updateTransaction(id, data) {
        return this.put(`/api/transactions/${id}`, data);
    },

    /**
     * 刪除交易
     */
    deleteTransaction(id) {
        return this.delete(`/api/transactions/${id}`);
    },

    /**
     * 取得分類列表
     */
    getCategories() {
        return this.get('/api/transactions/categories');
    },

    // ============ 統計 API ============

    /**
     * 取得統計摘要
     */
    getSummary(params = {}) {
        return this.get('/api/stats/summary', params);
    },

    /**
     * 取得分類統計
     */
    getCategoryStats(params = {}) {
        return this.get('/api/stats/by-category', params);
    },

    /**
     * 取得日期趨勢
     */
    getDateStats(params = {}) {
        return this.get('/api/stats/by-date', params);
    },

    // ============ 匯出 API ============

    /**
     * 匯出 CSV（返回下載 URL）
     */
    getExportCsvUrl(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return queryString ? `/api/export/csv?${queryString}` : '/api/export/csv';
    },

    /**
     * 匯出 Excel（返回下載 URL）
     */
    getExportExcelUrl(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return queryString ? `/api/export/excel?${queryString}` : '/api/export/excel';
    },
};

// 導出
window.API = API;
