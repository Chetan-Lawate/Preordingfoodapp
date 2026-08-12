/**
 * Admin Panel JavaScript
 * Handles real-time kitchen order status updates & menu audit toggles
 */

async function updateOrderStatus(orderId, newStatus) {
  try {
    const response = await fetch(`/admin/orders/${orderId}/status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ status: newStatus })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      showToast(`Order #${orderId} status updated to <strong>${newStatus.toUpperCase()}</strong>!`, 'success');
      
      const badge = document.getElementById(`status-badge-${orderId}`);
      if (badge) {
        if (newStatus === 'Ready') {
          badge.className = 'px-3.5 py-1 text-xs font-extrabold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 animate-pulse-fast';
          badge.textContent = '⚡ READY FOR PICKUP';
        } else if (newStatus === 'Cooking') {
          badge.className = 'px-3 py-1 text-xs font-extrabold rounded-full bg-blue-100 text-blue-800 border border-blue-200';
          badge.textContent = '🔥 COOKING IN KITCHEN';
        } else if (newStatus === 'Completed') {
          badge.className = 'px-3 py-1 text-xs font-bold rounded-full bg-slate-200 text-slate-700';
          badge.textContent = 'COMPLETED';
        } else {
          badge.className = 'px-3 py-1 text-xs font-bold rounded-full bg-amber-100 text-amber-800 border border-amber-200';
          badge.textContent = 'PENDING PREPARATION';
        }
      } else {
        setTimeout(() => window.location.reload(), 600);
      }
    } else {
      showToast(data.message || 'Failed to update order status.', 'danger');
    }
  } catch (err) {
    console.error(err);
    showToast('Error communicating with server.', 'danger');
  }
}
