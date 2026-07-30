/**
 * MatDan India - Election Reminder Service Worker
 */

self.addEventListener('push', function(event) {
    let data = { title: 'MatDan Election Portal', body: 'New election notification update!' };
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body || 'Voting portal update.',
        icon: '/static/images/badge_icon.png',
        badge: '/static/images/badge_icon.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url || '/'
        },
        actions: [
            { action: 'open_url', title: '🗳️ View Election' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'MatDan Election Reminder', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const urlToOpen = event.notification.data ? event.notification.data.url : '/';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (let i = 0; i < clientList.length; i++) {
                let client = clientList[i];
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});
