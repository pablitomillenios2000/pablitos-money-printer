const BACKEND_URL = "http://localhost:5080";

async function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
}

document.getElementById('subscribe').onclick = async () => {
    const registration = await navigator.serviceWorker.register('/sw.js');

    const vapidPublicKey = await fetch(`${BACKEND_URL}/vapidPublicKey`).then(res => res.text());
    const convertedVapidKey = await urlBase64ToUint8Array(vapidPublicKey);

    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: convertedVapidKey
    });

    await fetch(`${BACKEND_URL}/sendNotification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            subscription,
            payload: {
                title: "Hello from frontend!",
                body: "This is a push notification test."
            }
        })
    });

    console.log('Notification sent!');
};
