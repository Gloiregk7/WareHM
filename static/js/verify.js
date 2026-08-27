document.getElementById('verify-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const payload = {
        order_id: parseInt(document.getElementById('order_id').value),
        sku: document.getElementById('sku').value,
        batch_code: document.getElementById('batch_code').value,
        expiry_date: document.getElementById('expiry_date').value
    };

    const res = await fetch('/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    const alertContainer = document.getElementById('alert-container');

    if (data.result === 'APPROVED') {
        alertContainer.innerHTML = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle-fill me-2"></i><strong>APPROVED!</strong> Pick verified successfully.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>`;
    } else {
        alertContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i><strong>REJECTED!</strong> Errors: ${data.errors.join(', ')}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>`;
    }
});