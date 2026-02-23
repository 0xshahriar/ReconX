const Scans = {
    init() {
        const content = document.getElementById('dashboard-content');
        content.innerHTML = `
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold text-white">Scans</h2>
                <button onclick="Scans.showNewScanModal()" class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-sm font-medium">New Scan</button>
            </div>
            <div id="scans-list" class="space-y-4"></div>
        `;
        this.load();
    },

    load() {
        API.scans.list().then(data => {
            const container = document.getElementById('scans-list');
            container.innerHTML = data.map(scan => `
                <div class="glass-panel rounded-xl p-4 border border-slate-700/50">
                    <div class="flex items-center justify-between">
                        <div>
                            <h3 class="font-medium text-white">${scan.target_name}</h3>
                            <p class="text-sm text-slate-400">${scan.profile} • ${new Date(scan.started_at).toLocaleString()}</p>
                        </div>
                        <div class="flex items-center gap-3">
                            <span class="badge badge-${scan.status === 'running' ? 'green' : scan.status === 'completed' ? 'blue' : 'gray'}">${scan.status}</span>
                            ${scan.status === 'running' ? `
                                <button onclick="Scans.pause('${scan.id}')" class="text-yellow-400 hover:text-yellow-300">Pause</button>
                                <button onclick="Scans.stop('${scan.id}')" class="text-red-400 hover:text-red-300">Stop</button>
                            ` : ''}
                            <button onclick="Scans.view('${scan.id}')" class="text-sky-400 hover:text-sky-300">View</button>
                        </div>
                    </div>
                    ${scan.progress ? `
                        <div class="mt-3">
                            <div class="h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div class="h-full bg-sky-500" style="width: ${scan.progress}%"></div>
                            </div>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        });
    },

    showNewScanModal(targetId) {
        API.targets.list().then(targets => {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-content p-6 max-w-lg">
                    <h3 class="text-xl font-bold text-white mb-4">New Scan</h3>
                    <form id="new-scan-form" class="space-y-4">
                        <div>
                            <label class="block text-sm text-slate-300 mb-1">Target</label>
                            <select name="target_id" class="input-field" ${targetId ? 'disabled' : ''}>
                                ${targets.map(t => `<option value="${t.id}" ${t.id === targetId ? 'selected' : ''}>${t.name}</option>`).join('')}
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-slate-300 mb-1">Profile</label>
                            <select name="profile" class="input-field">
                                <option value="stealthy">Stealthy</option>
                                <option value="normal" selected>Normal</option>
                                <option value="aggressive">Aggressive</option>
                            </select>
                        </div>
                        <div class="flex justify-end gap-3 pt-4">
                            <button type="button" onclick="this.closest('.modal-overlay').remove()" class="btn btn-secondary">Cancel</button>
                            <button type="submit" class="btn btn-primary">Start Scan</button>
                        </div>
                    </form>
                </div>
            `;
            document.body.appendChild(modal);

            modal.querySelector('form').addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                API.scans.create({
                    target_id: formData.get('target_id'),
                    profile: formData.get('profile'),
                    modules: ['subdomain_enum', 'port_scan', 'http_probe', 'nuclei']
                }).then(() => {
                    modal.remove();
                    this.load();
                });
            });
        });
    },

    pause(id) {
        API.scans.pause(id).then(() => this.load());
    },

    stop(id) {
        if (confirm('Stop this scan?')) {
            API.scans.stop(id).then(() => this.load());
        }
    },

    view(id) {
        window.location.hash = 'dashboard';
        Dashboard.showActiveScan({ id });
    }
};
