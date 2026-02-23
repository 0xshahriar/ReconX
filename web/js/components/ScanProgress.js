const ScanProgress = {
    template: `
        <div class="scan-progress">
            <div class="flex items-center justify-between mb-4">
                <div>
                    <h3 class="font-semibold text-white" id="scan-target"></h3>
                    <p class="text-sm text-slate-400" id="scan-module"></p>
                </div>
                <div class="text-right">
                    <div class="text-2xl font-bold text-sky-400" id="scan-percent">0%</div>
                    <div class="text-xs text-slate-500" id="scan-eta">ETA: --:--</div>
                </div>
            </div>
            
            <div class="relative h-2 bg-slate-800 rounded-full overflow-hidden mb-4">
                <div id="scan-bar" class="absolute inset-y-0 left-0 bg-gradient-to-r from-sky-600 to-sky-400 transition-all duration-500" style="width: 0%"></div>
            </div>
            
            <div class="grid grid-cols-3 gap-4 text-center py-4 border-t border-slate-800">
                <div>
                    <div class="text-lg font-semibold text-white" id="stat-subdomains">0</div>
                    <div class="text-xs text-slate-500">Subdomains</div>
                </div>
                <div>
                    <div class="text-lg font-semibold text-white" id="stat-endpoints">0</div>
                    <div class="text-xs text-slate-500">Endpoints</div>
                </div>
                <div>
                    <div class="text-lg font-semibold text-red-400" id="stat-vulns">0</div>
                    <div class="text-xs text-slate-500">Vulnerabilities</div>
                </div>
            </div>
        </div>
    `,

    render(container) {
        container.innerHTML = this.template;
        this.bindEvents();
    },

    bindEvents() {
        WebSocketManager.on('scan_update', (data) => {
            this.update(data);
        });
    },

    update(data) {
        const target = document.getElementById('scan-target');
        const module = document.getElementById('scan-module');
        const percent = document.getElementById('scan-percent');
        const bar = document.getElementById('scan-bar');
        const eta = document.getElementById('scan-eta');
        const subdomains = document.getElementById('stat-subdomains');
        const endpoints = document.getElementById('stat-endpoints');
        const vulns = document.getElementById('stat-vulns');

        if (target) target.textContent = data.target_name || 'Unknown';
        if (module) module.textContent = data.current_module || 'Initializing...';
        if (percent) percent.textContent = (data.progress || 0) + '%';
        if (bar) bar.style.width = (data.progress || 0) + '%';
        if (eta) eta.textContent = 'ETA: ' + (data.eta || '--:--');
        if (subdomains) subdomains.textContent = data.stats?.subdomains || 0;
        if (endpoints) endpoints.textContent = data.stats?.endpoints || 0;
        if (vulns) vulns.textContent = data.stats?.vulnerabilities || 0;
    }
};
