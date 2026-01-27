/**
 * 認證相關功能
 */
const Auth = {
    user: null,

    /**
     * 檢查登入狀態
     */
    async checkAuth() {
        try {
            this.user = await API.getCurrentUser();
            return true;
        } catch (error) {
            return false;
        }
    },

    /**
     * 取得當前用戶
     */
    getUser() {
        return this.user;
    },

    /**
     * 登出
     */
    async logout() {
        try {
            await API.logout();
        } catch (error) {
            console.error('Logout error:', error);
        }
        window.location.href = '/static/index.html';
    },

    /**
     * 要求登入（未登入時導向登入頁）
     */
    async requireAuth() {
        const isLoggedIn = await this.checkAuth();
        if (!isLoggedIn) {
            window.location.href = '/static/index.html';
            return false;
        }
        return true;
    },

    /**
     * 初始化用戶資訊顯示
     */
    initUserDisplay() {
        if (!this.user) return;

        // 更新頭像
        const avatarElements = document.querySelectorAll('.user-avatar');
        avatarElements.forEach(el => {
            if (this.user.picture_url) {
                el.src = this.user.picture_url;
            }
        });

        // 更新名稱
        const nameElements = document.querySelectorAll('.user-name');
        nameElements.forEach(el => {
            el.textContent = this.user.display_name;
        });
    },

    /**
     * 綁定登出按鈕
     */
    bindLogoutButton() {
        const logoutButtons = document.querySelectorAll('.btn-logout');
        logoutButtons.forEach(btn => {
            btn.addEventListener('click', () => this.logout());
        });
    },
};

// 導出
window.Auth = Auth;
