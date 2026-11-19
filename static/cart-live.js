(() => {
  const forms = [...document.querySelectorAll('.inline-edit[data-product-id]')];
  if (!forms.length) return;
  const money = cents => new Intl.NumberFormat('en-US', {style:'currency', currency:'USD'}).format(cents / 100);
  const errorBox = document.getElementById('cart-error');
  const checkout = document.getElementById('checkout-link');
  const states = forms.map(form => ({
    form, input: form.querySelector('input[name="quantity"]'),
    line: form.closest('tr').querySelector('[data-line-subtotal]'),
    timer: null, chain: Promise.resolve(), dirty: false
  }));
  function error(message) {
    errorBox.textContent = message || '';
    errorBox.hidden = !message;
  }
  function updateDisplay() {
    let total = 0, itemCount = 0;
    for (const state of states) {
      const n = Number(state.input.value);
      const qty = Number.isInteger(n) && n >= 0 ? n : 0;
      const amount = Number(state.line.dataset.unitCents) * qty;
      state.line.textContent = money(amount);
      total += amount;
      if (qty > 0) itemCount++;
    }
    document.querySelector('[data-cart-total]').textContent = money(total);
    document.querySelector('[data-item-count]').textContent = itemCount;
  }
  function save(state) {
    clearTimeout(state.timer);
    state.timer = null;
    if (!state.dirty) return state.chain;
    if (!state.input.validity.valid || state.input.value === '') {
      error('Please enter a valid quantity.'); return state.chain;
    }
    state.dirty = false;
    const quantity = state.input.value;
    const params = new URLSearchParams(new FormData(state.form));
    state.chain = state.chain.catch(() => {}).then(async () => {
      const response = await fetch('/api/cart/quantity/' + state.form.dataset.productId, {
        method:'POST', body:params, credentials:'same-origin',
        headers:{'Accept':'application/json'}
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Unable to save cart');
      return result;
    }).catch(err => {error(err.message); state.dirty = true; throw err;});
    return state.chain;
  }
  for (const state of states) {
    state.input.addEventListener('input', () => {
      error('');
      state.dirty = true;
      updateDisplay();
      clearTimeout(state.timer);
      state.timer = setTimeout(() => save(state).catch(() => {}), 300);
    });
    state.input.addEventListener('blur', () => {if (state.dirty) save(state).catch(() => {});});
  }
  checkout.addEventListener('click', async event => {
    event.preventDefault();
    try {
      await Promise.all(states.map(save));
      if (states.some(s => s.dirty)) return;
      window.location.assign(checkout.href);
    } catch (_) { /* Error displayed inline. */ }
  });
})();
