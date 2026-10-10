/**
 * ShopZone E-Commerce Main JavaScript
 * Handles dynamic cart additions, toast notifications, quantity controls,
 * mobile drawer toggle, and client-side form helpers.
 */

// Toast Notification Manager
function showToast(message, type = 'success') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'success' ? '✓' : type === 'danger' ? '✕' : 'ℹ';
  toast.innerHTML = `<span style="font-weight: bold; font-size: 1.1rem;">${icon}</span> <span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Update Cart Badge count across the interface
function updateCartBadge(count) {
  const badges = document.querySelectorAll('.cart-badge');
  badges.forEach(badge => {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-flex' : 'none';
  });
}

// Quick Add to Cart via REST API
async function quickAddToCart(productId, quantity = 1, buttonElement = null) {
  let originalHtml = '';
  if (buttonElement) {
    originalHtml = buttonElement.innerHTML;
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<span>Adding...</span>';
  }

  try {
    const response = await fetch('/api/cart/add', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        product_id: productId,
        quantity: quantity
      })
    });

    const data = await response.json();

    if (data.success) {
      showToast(data.message || 'Added to cart!', 'success');
      updateCartBadge(data.cart_count);
    } else {
      showToast(data.error || 'Could not add to cart.', 'danger');
    }
  } catch (error) {
    console.error('Error adding to cart:', error);
    showToast('Network error while adding to cart.', 'danger');
  } finally {
    if (buttonElement) {
      buttonElement.disabled = false;
      buttonElement.innerHTML = originalHtml;
    }
  }
}

// Initialize interactive elements when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Menu Toggle
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const navLinks = document.getElementById('navLinks');
  if (mobileBtn && navLinks) {
    mobileBtn.addEventListener('click', () => {
      navLinks.classList.toggle('active');
    });
  }

  // 2. Quantity buttons (+ / -)
  document.querySelectorAll('.quantity-control').forEach(ctrl => {
    const minusBtn = ctrl.querySelector('.qty-minus');
    const plusBtn = ctrl.querySelector('.qty-plus');
    const input = ctrl.querySelector('.quantity-input');

    if (minusBtn && input) {
      minusBtn.addEventListener('click', () => {
        let val = parseInt(input.value) || 1;
        if (val > 1) {
          input.value = val - 1;
          input.dispatchEvent(new Event('change'));
        }
      });
    }

    if (plusBtn && input) {
      plusBtn.addEventListener('click', () => {
        let val = parseInt(input.value) || 1;
        let max = parseInt(input.getAttribute('max')) || 999;
        if (val < max) {
          input.value = val + 1;
          input.dispatchEvent(new Event('change'));
        } else {
          showToast(`Maximum available stock is ${max}.`, 'warning');
        }
      });
    }
  });

  // 3. Quick Add to Cart Buttons
  document.querySelectorAll('.btn-quick-add').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const productId = btn.getAttribute('data-product-id');
      quickAddToCart(productId, 1, btn);
    });
  });

  // 4. Payment Selection on Checkout Page
  const paymentLabels = document.querySelectorAll('.payment-radio-label');
  paymentLabels.forEach(label => {
    const radio = label.querySelector('input[type="radio"]');
    if (radio) {
      if (radio.checked) label.classList.add('active');
      radio.addEventListener('change', () => {
        paymentLabels.forEach(l => l.classList.remove('active'));
        if (radio.checked) label.classList.add('active');
      });
    }
  });

  // 5. Dismissible flash alert buttons
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) alert.remove();
    });
  });
});
