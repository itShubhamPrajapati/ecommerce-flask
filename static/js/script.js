// Shopping Cart Functions
function updateCart(productId, action) {
    fetch('/update-cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `product_id=${productId}&action=${action}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update cart count in navbar
            const cartCount = document.querySelector('.cart-count');
            if (cartCount) {
                cartCount.textContent = data.cart_count;
            }
            
            // Reload page to update cart
            setTimeout(() => {
                location.reload();
            }, 300);
        }
    });
}

function removeFromCart(productId) {
    updateCart(productId, 'remove');
}

// Product Rating Stars
function renderRating(stars) {
    let ratingHtml = '';
    const fullStars = Math.floor(stars);
    const hasHalfStar = stars % 1 >= 0.5;
    
    for (let i = 0; i < 5; i++) {
        if (i < fullStars) {
            ratingHtml += '<i class="fas fa-star"></i>';
        } else if (i === fullStars && hasHalfStar) {
            ratingHtml += '<i class="fas fa-star-half-alt"></i>';
        } else {
            ratingHtml += '<i class="far fa-star"></i>';
        }
    }
    
    return ratingHtml;
}

// Razorpay Payment
function proceedToPayment() {
    fetch('/create-order', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const options = {
                key: data.key,
                amount: data.amount,
                currency: data.currency,
                name: data.name,
                description: data.description,
                order_id: data.order_id,
                handler: function(response) {
                    // Submit payment success form
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/payment-success';
                    
                    const paymentId = document.createElement('input');
                    paymentId.type = 'hidden';
                    paymentId.name = 'razorpay_payment_id';
                    paymentId.value = response.razorpay_payment_id;
                    
                    const orderId = document.createElement('input');
                    orderId.type = 'hidden';
                    orderId.name = 'razorpay_order_id';
                    orderId.value = response.razorpay_order_id;
                    
                    form.appendChild(paymentId);
                    form.appendChild(orderId);
                    document.body.appendChild(form);
                    form.submit();
                },
                prefill: {
                    name: data.user.name,
                    email: data.user.email,
                    contact: data.user.phone || '9999999999'
                },
                theme: {
                    color: '#3b82f6'
                }
            };
            
            const rzp = new Razorpay(options);
            rzp.open();
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error creating order');
    });
}

// Form Validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.style.borderColor = '#ef4444';
        } else {
            input.style.borderColor = '';
        }
    });
    
    return isValid;
}

// Quantity Control
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('increase-qty')) {
        const input = e.target.previousElementSibling;
        input.value = parseInt(input.value) + 1;
    }
    
    if (e.target.classList.contains('decrease-qty')) {
        const input = e.target.nextElementSibling;
        if (parseInt(input.value) > 1) {
            input.value = parseInt(input.value) - 1;
        }
    }
});

// Auto-hide flash messages
setTimeout(function() {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        flash.style.transition = 'opacity 0.5s';
        flash.style.opacity = '0';
        setTimeout(() => flash.remove(), 500);
    });
}, 5000);

// Mobile Menu Toggle
function toggleMobileMenu() {
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Add rating stars to product cards
    document.querySelectorAll('.product-rating').forEach(ratingElement => {
        const rating = parseFloat(ratingElement.dataset.rating || 4.0);
        ratingElement.innerHTML = renderRating(rating);
    });
    
    // Add to cart buttons
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            fetch(`/add-to-cart/${productId}`)
                .then(() => {
                    // Update cart count
                    const cartCount = document.querySelector('.cart-count');
                    if (cartCount) {
                        const current = parseInt(cartCount.textContent) || 0;
                        cartCount.textContent = current + 1;
                    }
                    
                    // Show success message
                    alert('Product added to cart!');
                });
        });
    });
    
    // Checkout button
    const checkoutBtn = document.getElementById('checkout-btn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (validateForm('checkout-form')) {
                proceedToPayment();
            }
        });
    }
    
    // Payment button
    const payBtn = document.getElementById('pay-btn');
    if (payBtn) {
        payBtn.addEventListener('click', proceedToPayment);
    }
});