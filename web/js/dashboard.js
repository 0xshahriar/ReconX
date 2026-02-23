const Dashboard = {
    init() {
        this.render();
        this.bindEvents();
        this.loadData();
        
        WebSocketManager.on('system_stats', (data) => this.updateStats(data));
        WebSocketManager.on('scan_update', (data) => this.updateActiveScan(data));
    },

    render() {
        const root = document.getElementById('root');
        root.innerHTML = `
            <div id="connection-bar"><div id="connection-status"></div></div>
            
            <header class="fixed top-1 left-0 right-0 z-40 bg-slate-900/95 backdrop-blur border-b border-slate-800">
                <div class="flex items-center justify-between px-4 py-3">
                    <div class="flex items-center gap-3">
                        <button id="menu-toggle" class="lg:hidden p-2 rounded-lg hover:bg-slate-800">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
                        </button>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-sky-600 flex items-center justify-center font-bold text-white">R</div>
                            <h1 class="font-bold text-lg tracking-tight">ReconX</h1>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-2">
                        <div id="sys-status" class="hidden sm:flex items-center gap-3 text-xs mr-4">
                            <div class="flex items-center gap-1.5">
                                <span class="w-2 h-2 rounded-full bg-green-500 status-dot animate-pulse"></span>
                                <span class="text-slate-400">Online</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                                <span class="text-slate-400" id="battery-level">--%</span>
                            </div>
                            <div class="flex items-center gap-1.5">
                                <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>
                                <span class="text-slate-400" id="ram-usage">--GB</span>
                            </div>
                        </div>
                        
                        <button onclick="Dashboard.emergencyStop()" class="p-2 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20" title="Emergency Stop">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/></svg>
                        </button>
                    </div>
                </div>
            </header>

            <aside id="sidebar" class="sidebar">
                <nav class="p-4 space-y-1">
                    <a href="#dashboard" class="nav-item active flex items-center gap-3 px-3 py-2.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>
                        <span class="font-medium">Dashboard</span>
                    </a>
                    <a href="#targets" class="nav-item flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                        <span>Targets</span>
                    </a>
                    <a href="#scans" class="nav-item flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                        <span>Active Scans</span>
                    </a>
                    <a href="#vulnerabilities" class="nav-item flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                        <span>Vulnerabilities</span>
                    </a>
                    <a href="#wordlists" class="nav-item flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                        <span>Wordlists</span>
                    </a>
                    <a href="#settings" class="nav-item flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                        <span>Settings</span>
                    </a>
                </nav>
            </aside>

            <main class="lg:ml-64 pt-[57px] min-h-screen bg-slate-950">
                <div class="p-4 lg:p-6 max-w-7xl mx-auto">
                    <div id="dashboard-content">
                        <!-- Stats Grid -->
                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                            <div class="glass-panel rounded-xl p-4 border border-slate-700/50">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-slate-400 text-sm">Total Targets</span>
                                    <div class="w-8 h-8 rounded-lg bg-sky-500/10 flex items-center justify-center">
                                        <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                                    </div>
                                </div>
                                <div class="text-2xl font-bold text-white" id="stat-targets">-</div>
                            </div>
                            
                            <div class="glass-panel rounded-xl p-4 border border-slate-700/50">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-slate-400 text-sm">Active Scans</span>
                                    <div class="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center">
                                        <svg class="w-4 h-4 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                                    </div>
                                </div>
                                <div class="text-2xl font-bold text-white" id="stat-active">-</div>
                            </div>
                            
                            <div class="glass-panel rounded-xl p-4 border border-slate-700/50">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-slate-400 text-sm">Findings</span>
                                    <div class="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
                                        <svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                                    </div>
                                </div>
                                <div class="text-2xl font-bold text-white" id="stat-findings">-</div>
                            </div>
                            
                            <div class="glass-panel rounded-xl p-4 border border-slate-700/50">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-slate-400 text-sm">Subdomains</span>
                                    <div class="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
                                        <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>
                                    </div>
                                </div>
                                <div class="text-2xl font-bold text-white" id="stat-subdomains">-</div>
                            </div>
                        </div>

                        <div class="grid lg:grid-cols-3 gap-6">
                            <!-- Active Scan -->
                            <div class="lg:col-span-2 glass-panel rounded-xl p-6 border border-slate-700/50">
                                <div class="flex items-center justify-between mb-6">
                                    <h2 class="text-lg font-semibold text-white">Active Scan</h2>
                                    <div id="scan-controls" class="hidden flex gap-2">
                                        <button onclick="Dashboard.pauseScan()" class="px-3 py-1.5 rounded-lg bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20 text-sm font-medium">Pause</button>
                                        <button onclick="Dashboard.stopScan()" class="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-sm font-medium">Stop</button>
                                    </div>
                                </div>
                                <div id="scan-progress-container"></div>
                                <div id="terminal-container" class="mt-4"></div>
                            </div>

                            <!-- System Health -->
                            <div class="glass-panel rounded-xl p-6 border border-slate-700/50">
                                <h2 class="text-lg font-semibold text-white mb-6">System Health</h2>
                                <div id="system-stats"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        `;
    },

    bindEvents() {
        document.getElementById('menu-toggle')?.addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const view = item.getAttribute('href').substring(1);
                this.navigate(view);
            });
        });
    },

    navigate(view) {
        document.querySelectorAll('.nav-item').forEach(i => {
            i.classList.remove('active', 'bg-sky-500/10', 'text-sky-400', 'border', 'border-sky-500/20');
            i.classList.add('text-slate-400');
        });
        
        const active = document.querySelector(`a[href="#${view}"]`);
        if (active) {
            active.classList.add('active', 'bg-sky-500/10', 'text-sky-400', 'border', 'border-sky-500/20');
            active.classList.remove('text-slate-400');
        }

        switch(view) {
            case 'targets':
                Targets.init();
                break;
            case 'scans':
                Scans.init();
                break;
            case 'vulnerabilities':
                Vulnerabilities.init();
                break;
            case 'wordlists':
                Wordlists.init();
                break;
            case 'settings':
                Settings.init();
                break;
            default:
                this.loadData();
        }
    },

    loadData() {
        API.system.status().then(data => {
            this.updateStats(data);
        });

        API.targets.list().then(data => {
            document.getElementById('stat-targets').textContent = data.length;
        });

        API.scans.list().then(data => {
            const active = data.filter(s => s.status === 'running').length;
            document.getElementById('stat-active').textContent = active;
            
            if (active > 0) {
                const scan = data.find(s => s.status === 'running');
                this.showActiveScan(scan);
            }
        });
    },

    updateStats(data) {
        const memPercent = (data.memory.used / data.memory.total) * 100;
        const storagePercent = (data.storage.used / data.storage.total) * 100;

        const container = document.getElementById('system-stats');
        if (!container) return;

        container.innerHTML = `
            <div class="space-y-6">
                <div>
                    <div class="flex justify-between text-sm mb-2">
                        <span class="text-slate-400">Memory Usage</span>
                        <span class="text-white">${memPercent.toFixed(1)}%</span>
                    </div>
                    <div class="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div class="h-full bg-sky-500 transition-all duration-500" style="width: ${memPercent}%"></div>
                    </div>
                    <div class="mt-1 text-xs text-slate-500">${data.memory.used.toFixed(1)}GB / ${data.memory.total}GB</div>
                </div>

                <div>
                    <div class="flex justify-between text-sm mb-2">
                        <span class="text-slate-400">Storage</span>
                        <span class="text-white">${storagePercent.toFixed(1)}%</span>
                    </div>
                    <div class="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div class="h-full bg-green-500 transition-all duration-500" style="width: ${storagePercent}%"></div>
                    </div>
                    <div class="mt-1 text-xs text-slate-500">${data.storage.used}GB / ${data.storage.total}GB</div>
                </div>

                <div>
                    <div class="flex justify-between text-sm mb-2">
                        <span class="text-slate-400">CPU Load</span>
                        <span class="text-white">${data.cpu}%</span>
                    </div>
                    <div class="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div class="h-full bg-orange-500 transition-all duration-500" style="width: ${data.cpu}%"></div>
                    </div>
                </div>

                <div class="pt-4 border-t border-slate-800">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm text-slate-400">LLM Status</span>
                        <span class="text-xs px-2 py-0.5 rounded-full ${data.llm.loaded ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-300'}">
                            ${data.llm.loaded ? 'Active' : 'Unloaded'}
                        </span>
                    </div>
                    <div class="text-xs text-slate-500">${data.llm.model || 'No model loaded'}</div>
                </div>
            </div>
        `;

        document.getElementById('ram-usage').textContent = data.memory.used.toFixed(1) + 'GB';
        if (data.battery) {
            document.getElementById('battery-level').textContent = data.battery + '%';
        }
    },

    showActiveScan(scan) {
        document.getElementById('scan-controls').classList.remove('hidden');
        ScanProgress.render(document.getElementById('scan-progress-container'));
        LiveTerminal.render(document.getElementById('terminal-container'));
        
        WebSocketManager.subscribeToScan(scan.id);
    },

    updateActiveScan(data) {
        if (data.progress >= 100) {
            document.getElementById('scan-controls').classList.add('hidden');
        }
    },

    pauseScan() {
        const scanId = this.getCurrentScanId();
        if (scanId) API.scans.pause(scanId);
    },

    stopScan() {
        const scanId = this.getCurrentScanId();
        if (scanId && confirm('Stop current scan?')) {
            API.scans.stop(scanId);
        }
    },

    emergencyStop() {
        if (confirm('EMERGENCY STOP: Kill all scans?')) {
            API.system.emergencyStop();
        }
    },

    getCurrentScanId() {
        return null;
    }
};
