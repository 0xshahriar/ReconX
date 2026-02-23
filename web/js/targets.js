const Targets = {
    init() {
        const content = document.getElementById('dashboard-content');
        content.innerHTML = `
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold text-white">Targets</h2>
                <button onclick="Targets.showAddModal()" class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-sm font-medium flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                    Add Target
                </button>
            </div>
            <div id="targets-table" class="glass-panel rounded-xl overflow-hidden border border-slate-700/50"></div>
        `;
        this.load();
    },

    load() {
        API.targets.list().then(data => {
            const container = document.getElementById('targets-table');
            if (data.length === 0) {
                container.innerHTML = '<div class="p-8 text-center text-slate-500">No targets yet</div>';
                return;
            }

            container.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Target</th>
                            <th>Domain</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(t => `
                            <tr>
                                <td>
                                    <div class="font-medium text-white">${t.name}</div>
                                </td>
                                <td class="font-mono text-sm text-slate-400">${t.domain}</td>
                                <td>
                                    <span class="badge badge-${t.status === 'active' ? 'green' : 'gray'}">${t.status}</span>
                                </td>
                                <td>
                                    <button onclick="Targets.scan('${t.id}')" class="text-sky-400 hover:text-sky-300 text-sm mr-3">Scan</button>
                                    <button onclick="Targets.delete('${t.id}')" class="text-red-400 hover:text-red-300 text-sm">Delete</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        });
    },

    showAddModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content p-6">
                <h3 class="text-xl font-bold text-white mb-4">Add New Target</h3>
                <form id="add-target-form" class="space-y-4">
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">Name</label>
                        <input type="text" name="name" required class="input-field">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">Domain</label>
                        <input type="text" name="domain" required class="input-field" placeholder="example.com">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">Scope (one per line)</label>
                        <textarea name="scope" rows="3" class="input-field" placeholder="*.example.com"></textarea>
                    </div>
                    <div class="flex justify-end gap-3 pt-4">
                        <button type="button" onclick="this.closest('.modal-overlay').remove()" class="btn btn-secondary">Cancel</button>
                        <button type="submit" class="btn btn-primary">Add Target</button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(modal);

        modal.querySelector('form').addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            API.targets.create({
                name: formData.get('name'),
                domain: formData.get('domain'),
                scope: formData.get('scope').split('\n').filter(s => s.trim())
            }).then(() => {
                modal.remove();
                this.load();
            });
        });
    },

    scan(id) {
        window.location.hash = 'scans';
        Scans.showNewScanModal(id);
    },

    delete(id) {
        if (confirm('Delete this target?')) {
            API.targets.delete(id).then(() => this.load());
        }
    }
};
