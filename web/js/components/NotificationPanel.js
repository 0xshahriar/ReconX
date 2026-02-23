const NotificationPanel = {
    container: null,
    maxNotifications: 5,
    notifications: [],

    init() {
        this.container = document.createElement('div');
        this.container.className = 'notification-panel space-y-2';
        document.body.appendChild(this.container);

        WebSocketManager.on('notification', (data) => this.show(data));
    },

    show(data) {
        const id = Helpers.generateId();
        const notification = {
            id,
            type: data.type || 'info',
            title: data.title || 'Notification',
            message: data.message,
            timestamp: new Date()
        };

        this.notifications.unshift(notification);
        if (this.notifications.length > this.maxNotifications) {
            const removed = this.notifications.pop();
            this.removeFromDOM(removed.id);
        }

        this.renderNotification(notification);
        
        if (data.duration !== 0) {
            setTimeout(() => this.dismiss(id), data.duration || 5000);
        }
    },

    renderNotification(notification) {
        const colors = {
            success: 'border-green-500/50 bg-green-500/10',
            error: 'border-red-500/50 bg-red-500/10',
            warning: 'border-yellow-500/50 bg-yellow-500/10',
            info: 'border-sky-500/50 bg-sky-500/10'
        };

        const icons = {
            success: '<svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
            error: '<svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
            warning: '<svg class="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>',
            info: '<svg class="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
        };

        const el = document.createElement('div');
        el.id = `notif-${notification.id}`;
        el.className = `p-4 rounded-lg border ${colors[notification.type]} backdrop-blur shadow-lg transform translate-x-full transition-transform duration-300`;
        el.innerHTML = `
            <div class="flex items-start gap-3">
                ${icons[notification.type]}
                <div class="flex-1 min-w-0">
                    <h4 class="text-sm font-medium text-white">${notification.title}</h4>
                    <p class="text-xs text-slate-400 mt-1">${notification.message}</p>
                </div>
                <button onclick="NotificationPanel.dismiss('${notification.id}')" class="text-slate-500 hover:text-white">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            </div>
        `;

        this.container.appendChild(el);
        
        requestAnimationFrame(() => {
            el.classList.remove('translate-x-full');
        });
    },

    removeFromDOM(id) {
        const el = document.getElementById(`notif-${id}`);
        if (el) el.remove();
    },

    dismiss(id) {
        const el = document.getElementById(`notif-${id}`);
        if (!el) return;

        el.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => {
            el.remove();
            this.notifications = this.notifications.filter(n => n.id !== id);
        }, 300);
    }
};
