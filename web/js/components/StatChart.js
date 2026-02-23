const StatChart = {
    instances: new Map(),

    create(containerId, type, data, options = {}) {
        const canvas = document.getElementById(containerId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');
        
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: options.showLegend !== false,
                    labels: { color: '#94a3b8', font: { size: 11 } }
                }
            },
            scales: {
                x: {
                    display: type !== 'doughnut' && type !== 'pie',
                    grid: { color: '#1e293b' },
                    ticks: { color: '#64748b', font: { size: 10 } }
                },
                y: {
                    display: type !== 'doughnut' && type !== 'pie',
                    grid: { color: '#1e293b' },
                    ticks: { color: '#64748b', font: { size: 10 } }
                }
            }
        };

        const chart = new Chart(ctx, {
            type,
            data,
            options: { ...defaultOptions, ...options }
        });

        this.instances.set(containerId, chart);
        return chart;
    },

    update(containerId, newData) {
        const chart = this.instances.get(containerId);
        if (chart) {
            chart.data = newData;
            chart.update('none');
        }
    },

    destroy(containerId) {
        const chart = this.instances.get(containerId);
        if (chart) {
            chart.destroy();
            this.instances.delete(containerId);
        }
    },

    destroyAll() {
        this.instances.forEach(chart => chart.destroy());
        this.instances.clear();
    }
};
