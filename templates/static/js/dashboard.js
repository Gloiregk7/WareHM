async function loadDashboard() {
    const res = await fetch('/api/dashboard');
    const data = await res.json();

    document.getElementById('total-picks').innerText = data.total_picks;
    document.getElementById('approved-picks').innerText = data.approved;
    document.getElementById('rejected-picks').innerText = data.rejected;

    const tbody = document.getElementById('logs-table-body');
    if (data.recent_logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No audit logs recorded yet.</td></tr>';
        return;
    }

    tbody.innerHTML = data.recent_logs.map(log => `
        <tr>
            <td>#${log.log_id}</td>
            <td>#${log.order_id}</td>
            <td><code>${log.sku}</code></td>
            <td>${log.scanned_batch}</td>
            <td>${log.scanned_expiry}</td>
            <td><span class="badge ${log.result === 'APPROVED' ? 'bg-success' : 'bg-danger'}">${log.result}</span></td>
            <td>${log.error_codes ? `<span class="text-danger fw-bold">${log.error_codes}</span>` : 'None'}</td>
            <td>${log.timestamp}</td>
        </tr>
    `).join('');
}

loadDashboard();