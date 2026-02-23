const Vulnerabilities = {
    init() {
        const content = document.getElementById('dashboard-content');
        content.innerHTML = `
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold text-white">Vulnerabilities</h2>
                <div class="flex gap-2">
                    <select id="severity-filter" class="input-field text-sm w-32">
                        <option value="all">All Severities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
            </div>
            <div id="vulns-list" class="space-y-3"></div>
        `;
        this.load();

        document.getElementById('severity-filter')?.addEventListener('change', (e) => {
            this.load(e.target.value);
        });
    },

    load(severity = 'all') {
        API.scans.list().then(scans => {
            const container = document.getElementById('vulns-list');
            container.innerHTML = '';
            
            scans.forEach(scan => {
                API.scans.getVulnerabilities(scan.id).then(vulns => {
                    const filtered = severity === 'all' ? vulns : vulns.filter(v => v.severity === severity);
                    if (filtered.length > 0) {
                        VulnCard.render(container, filtered);
                    }
                });
            });
        });
    }
};
