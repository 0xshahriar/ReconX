const LiveTerminal = {
    maxLines: 500,
    lines: [],
    filter: 'all',

    template: `
        <div class="terminal-window border border-slate-800">
            <div class="terminal-header flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <div class="terminal-btn red"></div>
                    <div class="terminal-btn yellow"></div>
                    <div class="terminal-btn green"></div>
                </div>
                <div class="flex items-center gap-2">
                    <select id="terminal-filter" class="text-xs bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-300">
                        <option value="all">All Output</option>
                        <option value="info">Info</option>
                        <option value="error">Errors</option>
                        <option value="findings">Findings</option>
                    </select>
                    <button id="terminal-clear" class="text-xs text-slate-400 hover:text-white">Clear</button>
                    <button id="terminal-download" class="text-xs text-slate-400 hover:text-white">Download</button>
                </div>
            </div>
            <div id="terminal-body" class="terminal-body text-slate-300"></div>
        </div>
    `,

    render(container) {
        container.innerHTML = this.template;
        this.bindEvents();
        WebSocketManager.on('terminal_output', (line) => this.addLine(line));
    },

    bindEvents() {
        const filter = document.getElementById('terminal-filter');
        const clear = document.getElementById('terminal-clear');
        const download = document.getElementById('terminal-download');

        if (filter) {
            filter.addEventListener('change', (e) => {
                this.filter = e.target.value;
                this.renderLines();
            });
        }

        if (clear) {
            clear.addEventListener('click', () => this.clear());
        }

        if (download) {
            download.addEventListener('click', () => this.download());
        }
    },

    addLine(line) {
        const timestamp = new Date().toLocaleTimeString();
        const entry = { timestamp, text: line, type: this.classifyLine(line) };
        
        this.lines.push(entry);
        
        if (this.lines.length > this.maxLines) {
            this.lines.shift();
        }

        if (this.matchesFilter(entry)) {
            this.appendLineToDOM(entry);
        }
    },

    classifyLine(line) {
        if (line.includes('[ERROR]') || line.includes('error') || line.includes('failed')) return 'error';
        if (line.includes('[WARN]')) return 'warning';
        if (line.includes('found') || line.includes('discovered') || line.includes('vulnerable')) return 'finding';
        if (line.includes('[INFO]')) return 'info';
        return 'default';
    },

    matchesFilter(entry) {
        if (this.filter === 'all') return true;
        if (this.filter === 'error') return entry.type === 'error';
        if (this.filter === 'findings') return entry.type === 'finding';
        if (this.filter === 'info') return entry.type === 'info' || entry.type === 'default';
        return true;
    },

    appendLineToDOM(entry) {
        const body = document.getElementById('terminal-body');
        if (!body) return;

        const div = document.createElement('div');
        div.className = 'font-mono text-xs mb-1 ' + this.getColorClass(entry.type);
        div.innerHTML = `<span class="text-slate-600">[${entry.timestamp}]</span> ${Helpers.escapeHtml(entry.text)}`;

        body.appendChild(div);
        body.scrollTop = body.scrollHeight;

        while (body.children.length > this.maxLines) {
            body.removeChild(body.firstChild);
        }
    },

    getColorClass(type) {
        const colors = {
            error: 'text-red-400',
            warning: 'text-yellow-400',
            finding: 'text-green-400',
            info: 'text-blue-400',
            default: 'text-slate-300'
        };
        return colors[type] || colors.default;
    },

    renderLines() {
        const body = document.getElementById('terminal-body');
        if (!body) return;
        
        body.innerHTML = '';
        this.lines.filter(l => this.matchesFilter(l)).forEach(l => this.appendLineToDOM(l));
    },

    clear() {
        this.lines = [];
        const body = document.getElementById('terminal-body');
        if (body) body.innerHTML = '';
    },

    download() {
        const content = this.lines.map(l => `[${l.timestamp}] ${l.text}`).join('\n');
        Helpers.downloadFile(content, `reconx-terminal-${Date.now()}.log`);
    }
};
