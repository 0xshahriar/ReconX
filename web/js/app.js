const App = {
    init() {
        WebSocketManager.connect();
        NotificationPanel.init();
        Dashboard.init();
        
        window.addEventListener('hashchange', () => {
            const view = window.location.hash.substring(1) || 'dashboard';
            Dashboard.navigate(view);
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
