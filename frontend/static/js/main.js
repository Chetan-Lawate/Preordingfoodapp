/**
 * Food Pre-Ordering Application - Main JavaScript
 * Handles Cart Management, LocalStorage Persistence, Toast Notifications & Checkout
 */

const CART_KEY = 'preorder_food_cart';

// Cart Helper Functions
function getCart() {
  try {
    const raw = localStorage.getItem(CART_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error('Error loading cart from storage', e);
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartBadge();
  if (window.location.pathname === '/cart') {
    renderCartPage();
  }
}

function clearCart() {
  localStorage.removeItem(CART_KEY);
  updateCartBadge();
  if (window.location.pathname === '/cart') {
    renderCartPage();
  }
}

function getCartCount() {
  const cart = getCart();
  return cart.reduce((sum, item) => sum + item.quantity, 0);
}

function getCartTotal() {
  const cart = getCart();
  return cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
}

// Add Item to Cart with Toast Notification & Button Feedback
function addToCart(item, btnElement) {
  const cart = getCart();
  const existing = cart.find(i => i.id === item.id);
  
  if (existing) {
    existing.quantity += (item.quantity || 1);
  } else {
    cart.push({
      id: item.id,
      name: item.name || item.item_name,
      price: parseFloat(item.price),
      image_url: item.image_url,
      category: item.category || 'General',
      quantity: item.quantity || 1
    });
  }
  
  saveCart(cart);

  // Button feedback animation if button element passed
  if (btnElement && btnElement instanceof HTMLElement) {
    const originalContent = btnElement.innerHTML;
    btnElement.classList.add('bg-emerald-600', 'text-white');
    btnElement.classList.remove('bg-orange-50', 'text-brand-600');
    btnElement.innerHTML = '✓ Added to Cart!';
    setTimeout(() => {
      btnElement.innerHTML = originalContent;
      btnElement.classList.remove('bg-emerald-600', 'text-white');
      btnElement.classList.add('bg-orange-50', 'text-brand-600');
    }, 1400);
  }

  // Display prominent top-right notification option with "View Cart ->" button
  showAddToCartNotification(item);
}

// Dedicated "Added to Cart" Pop Notification Option
function showAddToCartNotification(item) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast toast-success bg-slate-900 text-white flex items-center justify-between gap-3 p-4 rounded-2xl shadow-2xl border-l-4 border-emerald-500';
  
  const itemName = item.name || item.item_name || 'Item';
  const itemPrice = parseFloat(item.price || 0).toFixed(2);
  const imgUrl = item.image_url || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=100';

  toast.innerHTML = `
    <div class="flex items-center gap-3 overflow-hidden">
      <img src="${imgUrl}" alt="${itemName}" class="w-10 h-10 object-cover rounded-xl flex-shrink-0 border border-slate-700">
      <div class="truncate">
        <span class="block text-[11px] font-extrabold text-emerald-400 uppercase tracking-wider">✓ Item Added to Cart</span>
        <span class="block text-xs font-bold text-white truncate">${itemName} (₹${itemPrice})</span>
      </div>
    </div>
    <div class="flex items-center gap-2 flex-shrink-0">
      <a href="/cart" class="px-3.5 py-1.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-extrabold shadow-xs transition">
        View Cart →
      </a>
      <button onclick="this.parentElement.parentElement.remove()" class="text-slate-400 hover:text-white font-bold ml-1 text-base">&times;</button>
    </div>
  `;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 350);
  }, 4000);
}

function removeFromCart(id) {
  let cart = getCart();
  const item = cart.find(i => i.id === id);
  cart = cart.filter(i => i.id !== id);
  saveCart(cart);
  if (item) {
    showToast(`Removed <strong>${item.name}</strong> from cart`, 'info');
  }
}

function updateQuantity(id, delta) {
  const cart = getCart();
  const item = cart.find(i => i.id === id);
  if (!item) return;

  item.quantity += delta;
  if (item.quantity <= 0) {
    removeFromCart(id);
  } else {
    saveCart(cart);
  }
}

// Update Cart Badge Counters in Navbar & Mobile Bar
function updateCartBadge() {
  const count = getCartCount();
  const total = getCartTotal();

  // Desktop & Mobile Navbar badges
  const badgeEls = document.querySelectorAll('.cart-count-badge');
  badgeEls.forEach(el => {
    el.textContent = count;
    if (count > 0) {
      el.classList.remove('hidden');
    } else {
      el.classList.add('hidden');
    }
  });

  // Floating Mobile Cart Bar
  const floatBar = document.getElementById('floating-cart-bar');
  const floatCount = document.getElementById('floating-cart-count');
  const floatTotal = document.getElementById('floating-cart-total');

  if (floatBar && floatCount && floatTotal) {
    if (count > 0 && window.location.pathname !== '/cart') {
      floatBar.classList.remove('translate-y-full', 'hidden');
      floatCount.textContent = count;
      floatTotal.textContent = `₹${total.toFixed(2)}`;
    } else {
      floatBar.classList.add('translate-y-full', 'hidden');
    }
  }
}

// General Toast Notification System
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let iconHtml = '✓';
  if (type === 'danger') iconHtml = '✕';
  if (type === 'warning') iconHtml = '⚠';
  if (type === 'info') iconHtml = 'ℹ';

  toast.innerHTML = `
    <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-white ${
      type === 'success' ? 'bg-emerald-500' :
      type === 'danger' ? 'bg-red-500' :
      type === 'warning' ? 'bg-amber-500' : 'bg-blue-500'
    }">${iconHtml}</div>
    <div class="flex-1 text-sm leading-snug">${message}</div>
    <button onclick="this.parentElement.remove()" class="text-gray-400 hover:text-gray-600 font-bold ml-2 text-base">&times;</button>
  `;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 350);
  }, 3500);
}

// Render Cart Page DOM
function renderCartPage() {
  const container = document.getElementById('cart-items-container');
  const emptyState = document.getElementById('cart-empty-state');
  const summaryBox = document.getElementById('cart-summary-box');
  const subtotalEl = document.getElementById('cart-subtotal');
  const totalEl = document.getElementById('cart-total');

  if (!container) return;

  const cart = getCart();

  if (cart.length === 0) {
    if (container) container.innerHTML = '';
    if (emptyState) emptyState.classList.remove('hidden');
    if (summaryBox) summaryBox.classList.add('hidden');
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');
  if (summaryBox) summaryBox.classList.remove('hidden');

  let html = '';
  cart.forEach(item => {
    const subtotal = item.price * item.quantity;
    html += `
      <div class="flex flex-col sm:flex-row items-center justify-between p-4 bg-white rounded-2xl shadow-sm border border-gray-100 mb-3 gap-4">
        <div class="flex items-center gap-4 w-full sm:w-auto">
          <img src="${item.image_url || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200'}" alt="${item.name}" class="w-16 h-16 object-cover rounded-xl flex-shrink-0 shadow-xs">
          <div>
            <h4 class="font-bold text-gray-900 leading-tight">${item.name}</h4>
            <p class="text-xs text-orange-600 font-medium">${item.category}</p>
            <p class="text-sm font-semibold text-gray-700 mt-1">₹${item.price.toFixed(2)} each</p>
          </div>
        </div>

        <div class="flex items-center justify-between w-full sm:w-auto gap-6 border-t sm:border-t-0 pt-3 sm:pt-0">
          <div class="flex items-center border border-gray-200 rounded-xl bg-gray-50">
            <button onclick="updateQuantity(${item.id}, -1)" class="w-8 h-8 flex items-center justify-center font-bold text-gray-600 hover:text-orange-600 transition">-</button>
            <span class="px-3 text-sm font-bold text-gray-800">${item.quantity}</span>
            <button onclick="updateQuantity(${item.id}, 1)" class="w-8 h-8 flex items-center justify-center font-bold text-gray-600 hover:text-orange-600 transition">+</button>
          </div>

          <div class="text-right">
            <span class="block font-bold text-gray-900 text-base">₹${subtotal.toFixed(2)}</span>
            <button onclick="removeFromCart(${item.id})" class="text-xs text-red-500 hover:text-red-700 font-semibold underline mt-0.5">Remove</button>
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
  const total = getCartTotal();
  if (subtotalEl) subtotalEl.textContent = `₹${total.toFixed(2)}`;
  if (totalEl) totalEl.textContent = `₹${total.toFixed(2)}`;
}

// Process Checkout Form
async function processCheckout(e) {
  if (e) e.preventDefault();

  const cart = getCart();
  if (cart.length === 0) {
    showToast('Your cart is empty! Browse the menu to add food items.', 'warning');
    return;
  }

  const breakTimeSelect = document.getElementById('break_time_select');
  if (!breakTimeSelect || !breakTimeSelect.value) {
    showToast('Please select your target break pickup time.', 'warning');
    if (breakTimeSelect) breakTimeSelect.focus();
    return;
  }

  const breakTime = breakTimeSelect.value;
  const btn = document.getElementById('btn-checkout-submit');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg> Processing Order...
    `;
  }

  try {
    const response = await fetch('/checkout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        items: cart.map(i => ({ id: i.id, quantity: i.quantity })),
        break_time: breakTime
      })
    });

    const res = await response.json();

    if (response.status === 401) {
      showToast(res.message || 'Please sign in to complete your pre-order.', 'warning');
      setTimeout(() => {
        window.location.href = res.redirect || '/login?next=/cart';
      }, 1000);
      return;
    }

    if (response.ok && res.success) {
      clearCart();
      showToast(res.message, 'success');
      setTimeout(() => {
        window.location.href = '/orders';
      }, 1200);
    } else {
      showToast(res.message || 'Checkout failed. Please log in or try again.', 'danger');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = 'Confirm & Pre-Order Now';
      }
    }
  } catch (err) {
    console.error('Checkout error:', err);
    showToast('An unexpected error occurred during checkout. Please try again.', 'danger');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = 'Confirm & Pre-Order Now';
    }
  }
}

// Global Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  updateCartBadge();
  if (window.location.pathname === '/cart') {
    renderCartPage();
    const checkoutForm = document.getElementById('checkout-form');
    if (checkoutForm) {
      checkoutForm.addEventListener('submit', processCheckout);
    }
  }
});
