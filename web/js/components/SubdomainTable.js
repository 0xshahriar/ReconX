const SubdomainTable = {
    columns: [
        { key: 'subdomain', label: 'Subdomain', sortable: true },
        { key: 'ip_addresses', label: 'IP Address', sortable: false },
        { key: 'status_code', label: 'Status', sortable: true },
        { key: 'tech_stack', label: 'Technology', sortable: false },
        { key: 'actions', label: '', sortable: false }
    ],

    template() {
        return `
            <div class="subdomain-table">
                <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center gap-2">
                        <input type="text" id="subdomain-search" placeholder="Search subdomains..." class="input-field text-sm w-64">
                        <select id="subdomain-filter" class="input-field text-sm w-32">
                            <option value="all">All</option>
                            <option value="live">Live</option>
                            <option value="dead">Dead</option>
                        </select>
                    </div>
                    <button id="subdomain-export" class="btn btn-secondary text-sm">Export CSV</button>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="data-table">
                        <thead>
                            <tr>
                                ${this.columns.map(col => `
                                    <th class="${col.sortable ? 'cursor-pointer hover:text-white' : ''}" data-sort="${col.key}">
                                        ${col.label}
                                        ${col.sortable ? '<span class="sort-icon ml-1 text-slate-600">↕</span>' : ''}
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>
                        <tbody id="subdomain-tbody"></tbody>
                    </table>
                </div>
                
                <div class="flex items-center justify-between mt-4 text-sm text-slate-500">
                    <span id="subdomain-count">0 results</span>
                    <div class="flex gap-2">
                        <button id="prev-page" class="btn btn-secondary text-xs" disabled>Previous</button>
                        <button id="next-page" class="btn btn-secondary text-xs" disabled>Next</button>
                    </div>
                </div>
            </div>
        `;
    },

    render(container, data = []) {
        container.innerHTML = this.template();
        this.data = data;
        this.filteredData = [...data];
        this.currentPage = 1;
        this.pageSize = 20;
        this.sortColumn = null;
        this.sortDirection = 'asc';
        
        this.bindEvents();
        this.renderTable();
    },

    bindEvents() {
        const search = document.getElementById('subdomain-search');
        const filter = document.getElementById('subdomain-filter');
        const exportBtn = document.getElementById('subdomain-export');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');

        if (search) {
            search.addEventListener('input', Helpers.debounce((e) => {
                this.filterData(e.target.value, filter?.value);
            }, 300));
        }

        if (filter) {
            filter.addEventListener('change', (e) => {
                this.filterData(search?.value || '', e.target.value);
            });
        }

        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportCSV());
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.renderTable();
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const maxPage = Math.ceil(this.filteredData.length / this.pageSize);
                if (this.currentPage < maxPage) {
                    this.currentPage++;
                    this.renderTable();
                }
            });
        }

        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const key = th.dataset.sort;
                this.sortData(key);
            });
        });
    },

    filterData(searchTerm, filterType) {
        this.filteredData = this.data.filter(item => {
            const matchesSearch = !searchTerm || 
                item.subdomain.toLowerCase().includes(searchTerm.toLowerCase());
            
            let matchesFilter = true;
            if (filterType === 'live') matchesFilter = item.is_live === true;
            if (filterType === 'dead') matchesFilter = item.is_live === false;
            
            return matchesSearch && matchesFilter;
        });
        
        this.currentPage = 1;
        this.renderTable();
    },

    sortData(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }

        this.filteredData.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];
            
            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }
            
            if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        this.renderTable();
    },

    renderTable() {
        const tbody = document.getElementById('subdomain-tbody');
        const count = document.getElementById('subdomain-count');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');

        if (!tbody) return;

        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        const pageData = this.filteredData.slice(start, end);

        tbody.innerHTML = pageData.map(item => `
            <tr>
                <td>
                    <div class="font-mono text-sm text-sky-400">${item.subdomain}</div>
                    <div class="text-xs text-slate-500">${item.source?.join(', ') || 'unknown'}</div>
                </td>
                <td>
                    ${item.ip_addresses?.map(ip => `<div class="text-sm text-slate-300 font-mono">${ip}</div>`).join('') || '-'}
                </td>
                <td>
                    <span class="inline-flex items-center px-2 py-1 rounded text-xs ${item.status_code >= 200 && item.status_code < 300 ? 'bg-green-500/10 text-green-400' : item.status_code >= 400 ? 'bg-red-500/10 text-red-400' : 'bg-slate-700 text-slate-300'}">
                        ${item.status_code || '-'}
                    </span>
                </td>
                <td>
                    <div class="flex flex-wrap gap-1">
                        ${item.tech_stack?.map(tech => `<span class="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400">${tech}</span>`).join('') || '-'}
                    </div>
                </td>
                <td>
                    <button onclick="SubdomainTable.viewDetails('${item.id}')" class="text-sky-400 hover:text-sky-300 text-sm">Details</button>
                </td>
            </tr>
        `).join('');

        if (count) count.textContent = `${this.filteredData.length} results`;
        if (prevBtn) prevBtn.disabled = this.currentPage === 1;
        if (nextBtn) nextBtn.disabled = this.currentPage >= Math.ceil(this.filteredData.length / this.pageSize);
    },

    exportCSV() {
        const headers = this.columns.filter(c => c.key !== 'actions').map(c => c.label).join(',');
        const rows = this.filteredData.map(item => [
            item.subdomain,
            item.ip_addresses?.join(';') || '',
            item.status_code || '',
            item.tech_stack?.join(';') || ''
        ].join(',')).join('\n');
        
        Helpers.downloadFile(`${headers}\n${rows}`, `subdomains-${Date.now()}.csv`, 'text/csv');
    },

    viewDetails(id) {
        API.get(`/subdomains/${id}`).then(data => {
            // Show modal with details
            console.log('Subdomain details:', data);
        });
    }
};
