const VulnCard = {
    template(data) {
        const severityClass = Helpers.getSeverityBg(data.severity);
        
        return `
            <div class="vuln-card ${data.severity} glass-panel rounded-lg p-4 mb-3 ${severityClass}" data-id="${data.id}">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="badge badge-${data.severity} uppercase">${data.severity}</span>
                            <span class="text-xs text-slate-500">${data.tool_source}</span>
                        </div>
                        <h4 class="font-semibold text-white mb-1">${data.title}</h4>
                        <p class="text-sm text-slate-400 mb-2">${data.affected_url}</p>
                        ${data.parameter ? `<code class="text-xs bg-slate-950 px-2 py-1 rounded text-sky-400">${data.parameter}</code>` : ''}
                    </div>
                    <button class="expand-btn p-2 hover:bg-slate-800 rounded-lg transition-colors">
                        <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                    </button>
                </div>
                
                <div class="details hidden mt-4 pt-4 border-t border-slate-800">
                    <div class="space-y-3">
                        <div>
                            <h5 class="text-xs font-medium text-slate-500 uppercase mb-1">Description</h5>
                            <p class="text-sm text-slate-300">${data.description || 'No description available'}</p>
                        </div>
                        
                        ${data.evidence ? `
                        <div>
                            <h5 class="text-xs font-medium text-slate-500 uppercase mb-1">Evidence</h5>
                            <pre class="text-xs bg-slate-950 p-3 rounded overflow-x-auto text-slate-400 font-mono">${Helpers.escapeHtml(data.evidence)}</pre>
                        </div>
                        ` : ''}
                        
                        ${data.poc_commands?.length ? `
                        <div>
                            <h5 class="text-xs font-medium text-slate-500 uppercase mb-1">Proof of Concept</h5>
                            <div class="space-y-2">
                                ${data.poc_commands.map(cmd => `
                                    <div class="flex items-center gap-2 bg-slate-950 p-2 rounded">
                                        <code class="text-xs text-sky-400 font-mono flex-1 overflow-x-auto">${Helpers.escapeHtml(cmd)}</code>
                                        <button onclick="Helpers.copyToClipboard('${Helpers.escapeHtml(cmd)}')" class="text-xs text-slate-500 hover:text-white">Copy</button>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                        
                        ${data.remediation ? `
                        <div>
                            <h5 class="text-xs font-medium text-slate-500 uppercase mb-1">Remediation</h5>
                            <p class="text-sm text-slate-300">${data.remediation}</p>
                        </div>
                        ` : ''}
                        
                        <div class="flex gap-2 pt-2">
                            <button class="btn btn-secondary text-xs" onclick="VulnCard.markAsFP('${data.id}')">False Positive</button>
                            <button class="btn btn-primary text-xs" onclick="VulnCard.generateReport('${data.id}')">Generate Report</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    render(container, data) {
        container.innerHTML = data.map(v => this.template(v)).join('');
        this.bindEvents(container);
    },

    bindEvents(container) {
        container.querySelectorAll('.expand-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const card = e.target.closest('.vuln-card');
                const details = card.querySelector('.details');
                const icon = btn.querySelector('svg');
                
                details.classList.toggle('hidden');
                icon.style.transform = details.classList.contains('hidden') ? '' : 'rotate(180deg)';
            });
        });
    },

    markAsFP(id) {
        API.post(`/vulnerabilities/${id}/mark-fp`, { false_positive: true })
            .then(() => {
                const card = document.querySelector(`[data-id="${id}"]`);
                if (card) card.remove();
            });
    },

    generateReport(id) {
        API.post('/reports/generate', { vuln_id: id, format: 'pdf' })
            .then(() => alert('Report generation started'));
    }
};
