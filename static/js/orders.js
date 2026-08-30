async function loadOrders() {
    const res = await fetch('/api/orders');
    const orders = await res.json();
    const tbody = document.getElementById('orders-table-body');
    
    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No dispatch orders available.</td></tr>';
        return;
    }

    tbody.innerHTML = orders.map(order => `
        <tr>
            <td><strong>#${order.order_id}</strong></td>
            <td><code>${order.sku}</code></td>
            <td>${order.item_name}</td>
            <td><span class="badge bg-secondary">${order.target_batch}</span></td>
            <td>${order.expiry_date}</td>
            <td><i class="bi bi-geo-alt me-1"></i>${order.location}</td>
            <td>${order.hospital_name || order.destination}</td>
            <td><span class="badge ${order.status === 'READY_FOR_DISPATCH' ? 'bg-success' : 'bg-warning text-dark'}">${order.status_label || order.status.replaceAll('_', ' ')}</span></td>
            <td>${order.status === 'PENDING' ? `<a class="btn btn-sm btn-primary" href="/verify?order_id=${order.order_id}"><i class="bi bi-qr-code-scan me-1"></i>Verify order</a>` : '<span class="text-success small"><i class="bi bi-check-circle me-1"></i>Verified</span>'}</td>
        </tr>
    `).join('');
}

async function deleteOrder(orderId) {
    if (!confirm(`Delete order #${orderId}? This is allowed only before verification.`)) return;
    const response = await fetch(`/api/orders/${orderId}`, {method: 'DELETE'});
    const result = await response.json();
    const message = document.getElementById('order-message');
    message.innerHTML = `<div class="alert alert-${response.ok ? 'success' : 'danger'}">${result.message}</div>`;
    if (response.ok) await loadOrders();
}

loadOrders();