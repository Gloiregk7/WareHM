async function loadOrders() {
    const res = await fetch('/api/orders');
    const orders = await res.json();
    const tbody = document.getElementById('orders-table-body');
    
    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No pending orders.</td></tr>';
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
            <td>${order.destination}</td>
            <td><span class="badge bg-warning text-dark">${order.status}</span></td>
        </tr>
    `).join('');
}

loadOrders();