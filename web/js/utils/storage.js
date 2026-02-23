const Storage = {
    prefix: 'reconx_',

    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(this.prefix + key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage get error:', e);
            return defaultValue;
        }
    },

    set(key, value) {
        try {
            localStorage.setItem(this.prefix + key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('Storage set error:', e);
            return false;
        }
    },

    remove(key) {
        localStorage.removeItem(this.prefix + key);
    },

    clear() {
        Object.keys(localStorage)
            .filter(k => k.startsWith(this.prefix))
            .forEach(k => localStorage.removeItem(k));
    },

    getSettings() {
        return this.get('settings', {
            theme: 'dark',
            notifications: true,
            autoRefresh: true,
            refreshInterval: 5000
        });
    },

    setSettings(settings) {
        return this.set('settings', settings);
    },

    getRecentTargets() {
        return this.get('recent_targets', []);
    },

    addRecentTarget(target) {
        const recent = this.getRecentTargets();
        const filtered = recent.filter(t => t.id !== target.id);
        filtered.unshift({ ...target, accessed: new Date().toISOString() });
        this.set('recent_targets', filtered.slice(0, 10));
    },

    getCachedData(key) {
        const cached = this.get('cache_' + key);
        if (!cached) return null;
        if (cached.expiry && new Date(cached.expiry) < new Date()) {
            this.remove('cache_' + key);
            return null;
        }
        return cached.data;
    },

    setCachedData(key, data, ttlMinutes = 5) {
        const expiry = new Date(Date.now() + ttlMinutes * 60000).toISOString();
        this.set('cache_' + key, { data, expiry });
    }
};
