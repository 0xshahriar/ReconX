const Settings = {
    init() {
        const content = document.getElementById('dashboard-content');
        content.innerHTML = `
            <h2 class="text-2xl font-bold text-white mb-6">Settings</h2>
            <div class="grid lg:grid-cols-2 gap-6">
                <div class="glass-panel rounded-xl p-6 border border-slate-700/50">
                    <h3 class="font-semibold text-white mb-4">General</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm text-slate-300 mb-1">Default Scan Profile</label>
                            <select id="setting-profile" class="input-field">
                                <option value="stealthy">Stealthy</option>
                                <option value="normal">Normal</option>
                                <option value="aggressive">Aggressive</option>
                            </select>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-slate-300">Auto-pause on Disconnect</span>
                            <input type="checkbox" id="setting-autopause" checked class="rounded bg-slate-800 border-slate-600 text-sky-500">
                        </div>
                    </div>
                </div>

                <div class="glass-panel rounded-xl p-6 border border-slate-700/50">
                    <h3 class="font-semibold text-white mb-4">Notifications</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm text-slate-300 mb-1">Discord Webhook</label>
                            <input type="url" id="setting-discord" class="input-field" placeholder="https://discord.com/api/webhooks/...">
                        </div>
                    </div>
                </div>

                <div class="glass-panel rounded-xl p-6 border border-slate-700/50">
                    <h3 class="font-semibold text-white mb-4">LLM</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm text-slate-300 mb-1">Ollama Endpoint</label>
                            <input type="url" id="setting-ollama" class="input-field" value="http://localhost:11434">
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-slate-300">Auto-scale Models</span>
                            <input type="checkbox" id="setting-autoscale" checked class="rounded bg-slate-800 border-slate-600 text-sky-500">
                        </div>
                    </div>
                </div>
            </div>
            <div class="flex justify-end gap-3 mt-6">
                <button onclick="Settings.reset()" class="btn btn-secondary">Reset</button>
                <button onclick="Settings.save()" class="btn btn-primary">Save Settings</button>
            </div>
        `;
        
        this.load();
    },

    load() {
        const settings = Storage.getSettings();
        document.getElementById('setting-profile').value = settings.profile || 'normal';
        document.getElementById('setting-autopause').checked = settings.autoPause !== false;
        document.getElementById('setting-autoscale').checked = settings.autoScale !== false;
    },

    save() {
        const settings = {
            profile: document.getElementById('setting-profile').value,
            autoPause: document.getElementById('setting-autopause').checked,
            autoScale: document.getElementById('setting-autoscale').checked,
            discord: document.getElementById('setting-discord').value,
            ollama: document.getElementById('setting-ollama').value
        };
        Storage.setSettings(settings);
        NotificationPanel.show({ type: 'success', title: 'Settings Saved', message: 'Your preferences have been updated' });
    },

    reset() {
        Storage.setSettings({});
        this.load();
    }
};
