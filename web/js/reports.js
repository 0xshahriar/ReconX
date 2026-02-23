const Reports = {
    init() {
        const content = document.getElementById('dashboard-content');
        content.innerHTML = `
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold text-white">Reports</h2>
            </div>
            <div id="reports-list" class="glass-panel rounded-xl border border-slate-700/50"></div>
        `;
        this.load();
    },

    load() {
        API.reports.list().then(data => {
            const container = document.getElementById('reports-list');
            container.innerHTML = data.length === 0 ? 
                '<div class="p-8 text-center text-slate-500">No reports generated yet</div>' :
                `<table class="data-table">
                    <thead>
                        <tr>
                            <th>Report</th>
                            <th>Format</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(r => `
                            <tr>
                                <td class="text-white">${r.name}</td>
                                <td><span class="badge badge-blue uppercase">${r.format}</span></td>
                                <td class="text-slate-400">${Helpers.formatDate(r.created_at)}</td>
                                <td>
                                    <button onclick="Reports.download('${r.id}')" class="text-sky-400 hover:text-sky-300 text-sm">Download</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>`;
        });
    },

    download(id) {
        API.reports.download(id);
    }
};
