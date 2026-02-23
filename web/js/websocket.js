const WebSocketManager = {
    ws: null,
    reconnectInterval: 5000,
    maxReconnectAttempts: 10,
    reconnectAttempts: 0,
    listeners: new Map(),
    isManualClose: false,

    connect() {
        if (this.ws?.readyState === WebSocket.OPEN) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/system`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.emit('connection', { status: 'connected' });
            this.updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('WebSocket message parse error:', e);
            }
        };

        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => this.connect(), this.reconnectInterval);
            }
            this.emit('connection', { status: 'disconnected' });
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };
    },

    disconnect() {
        this.isManualClose = true;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    },

    handleMessage(data) {
        this.emit(data.type, data.payload);
    },

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    },

    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    },

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error('Event handler error:', e);
                }
            });
        }
    },

    updateConnectionStatus(connected) {
        const bar = document.getElementById('connection-status');
        if (bar) {
            bar.className = connected ? 
                'h-full w-full bg-green-500 transition-all duration-500' : 
                'h-full w-full bg-red-500 transition-all duration-500';
        }
    },

    subscribeToScan(scanId) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                action: 'subscribe',
                scan_id: scanId
            }));
        }
    },

    unsubscribeFromScan(scanId) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                action: 'unsubscribe',
                scan_id: scanId
            }));
        }
    }
};
