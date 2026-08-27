const inventoryForm = document.getElementById('inventory-form');
const inventoryBody = document.getElementById('inventory-table-body');
const inventoryMessage = document.getElementById('inventory-message');

function showInventoryMessage(message, type) {
    inventoryMessage.innerHTML = `<div class="alert alert-${type}" role="alert">${message}</div>`;
}

async function loadInventory() {
    inventoryBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Loading inventory...</td></tr>';
    try {
        const response = await fetch('/api/inventory');
        const items = await response.json();
        if (!response.ok) throw new Error(items.message || 'Unable to load inventory');
        if (items.length === 0) {
            inventoryBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No inventory items yet.</td></tr>';
            return;
        }
        inventoryBody.innerHTML = items.map(item => `
            <tr>
                <td><strong>${item.sku}</strong></td>
                <td>${item.item_name}</td>
                <td><span class="badge bg-secondary">${item.batch_code}</span></td>
                <td>${item.quantity}</td>
                <td>${item.location}</td>
                <td>${item.expiry_date}</td>
            </tr>
        `).join('');
    } catch (error) {
        inventoryBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Unable to load inventory.</td></tr>';
        showInventoryMessage(error.message, 'danger');
    }
}

inventoryForm.addEventListener('submit', async event => {
    event.preventDefault();
    const formData = new FormData(inventoryForm);
    const payload = Object.fromEntries(formData.entries());
    payload.quantity = Number(payload.quantity);

    try {
        const response = await fetch('/api/inventory', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.message || 'Unable to add item');
        inventoryForm.reset();
        showInventoryMessage('Inventory item added successfully.', 'success');
        await loadInventory();
    } catch (error) {
        showInventoryMessage(error.message, 'danger');
    }
});

loadInventory();
