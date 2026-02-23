const API = {
    baseUrl: '',
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}/api${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ message: 'Request failed' }));
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    post(endpoint, body) {
        return this.request(endpoint, { method: 'POST', body });
    },

    put(endpoint, body) {
        return this.request(endpoint, { method: 'PUT', body });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    targets: {
        list() {
            return API.get('/targets');
        },
        get(id) {
            return API.get(`/targets/${id}`);
        },
        create(data) {
            return API.post('/targets', data);
        },
        delete(id) {
            return API.delete(`/targets/${id}`);
        }
    },

    scans: {
        list() {
            return API.get('/scans');
        },
        get(id) {
            return API.get(`/scans/${id}`);
        },
        create(data) {
            return API.post('/scans', data);
        },
        pause(id) {
            return API.post(`/scans/${id}/pause`);
        },
        resume(id) {
            return API.post(`/scans/${id}/resume`);
        },
        stop(id) {
            return API.post(`/scans/${id}/stop`);
        },
        delete(id) {
            return API.delete(`/scans/${id}`);
        },
        getSubdomains(id) {
            return API.get(`/scans/${id}/subdomains`);
        },
        getEndpoints(id) {
            return API.get(`/scans/${id}/endpoints`);
        },
        getVulnerabilities(id) {
            return API.get(`/scans/${id}/vulnerabilities`);
        },
        getPorts(id) {
            return API.get(`/scans/${id}/ports`);
        }
    },

    system: {
        status() {
            return API.get('/system/status');
        },
        pause() {
            return API.post('/system/pause');
        },
        resume() {
            return API.post('/system/resume');
        },
        emergencyStop() {
            return API.post('/system/emergency-stop');
        }
    },

    llm: {
        status() {
            return API.get('/llm/status');
        },
        switch(model) {
            return API.post('/llm/switch', { model });
        },
        unload() {
            return API.post('/llm/unload');
        }
    },

    wordlists: {
        list() {
            return API.get('/wordlists');
        },
        update() {
            return API.post('/wordlists/update');
        },
        upload(formData) {
            return fetch(`${this.baseUrl}/api/wordlists/upload`, {
                method: 'POST',
                body: formData
            }).then(r => r.json());
        }
    },

    reports: {
        list() {
            return API.get('/reports');
        },
        generate(scanId, format) {
            return API.post('/reports/generate', { scan_id: scanId, format });
        },
        download(id) {
            window.open(`${this.baseUrl}/api/reports/${id}/download`);
        }
    },

    tunnel: {
        start() {
            return API.post('/tunnel/start');
        },
        stop() {
            return API.post('/tunnel/stop');
        },
        status() {
            return API.get('/tunnel/status');
        }
    }
};
