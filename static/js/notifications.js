/**
 * MatDan Push Notifications Client Helper
 */

document.addEventListener('DOMContentLoaded', () => {
    const notifyBtn = document.getElementById('btnNotifyToggle');

    if ('serviceWorker' in navigator && 'PushManager' in window) {
        navigator.serviceWorker.register('/sw.js').then(reg => {
            console.log('Service Worker registered successfully for election reminders.');
        }).catch(err => {
            console.warn('Service Worker registration failed:', err);
        });
    }

    if (notifyBtn) {
        // Update button state based on current permission
        if (Notification.permission === 'granted') {
            notifyBtn.classList.remove('btn-outline-light');
            notifyBtn.classList.add('btn-warning');
            notifyBtn.title = 'Election Reminders Active 🔔';
        }

        notifyBtn.addEventListener('click', async () => {
            if (!('Notification' in window)) {
                alert('This browser does not support desktop notifications.');
                return;
            }

            if (Notification.permission === 'granted') {
                showDemoNotification('🔔 Election Reminders Active!', 'You will receive notifications when elections start or end.');
                return;
            }

            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                notifyBtn.classList.remove('btn-outline-light');
                notifyBtn.classList.add('btn-warning');
                showDemoNotification('🔔 Reminders Activated!', 'You will now receive instant push notifications for election schedules.');

                try {
                    const reg = await navigator.serviceWorker.ready;
                    const sub = await reg.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: urlBase64ToUint8Array('BEl62iUYgUivxIkv69yViEuiBIj-m91ApH19U16viEui')
                    });
                    
                    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
                    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

                    await fetch('/api/push-subscribe', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify(sub)
                    });
                } catch (e) {
                    console.log('Push subscription notice:', e);
                }
            } else {
                alert('Notifications blocked. You can enable them anytime in browser settings.');
            }
        });
    }

    function showDemoNotification(title, body) {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then(reg => {
                reg.showNotification(title, {
                    body: body,
                    icon: '/static/images/badge_icon.png',
                    vibrate: [100, 50, 100]
                });
            });
        } else {
            new Notification(title, { body: body });
        }
    }

    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
});
