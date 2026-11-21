'use strict';
const quoteForm = document.querySelector('#quote-form');
if (quoteForm) {
  const shipping = document.querySelector('#shipping-fields');
  const items = document.querySelector('#quote-items');
  const total = document.querySelector('#quote-total');
  const error = document.querySelector('#quote-error');
  const liveStatus = document.querySelector('#quote-status');
  let controller, timer;
  const money = new Intl.NumberFormat('es-MX', {style:'currency',currency:'MXN'});
  function updateShipping() {
    const enabled = quoteForm.querySelector('[name=delivery]:checked')?.value === 'shipping';
    shipping.hidden = !enabled;
    shipping.querySelectorAll('input').forEach(input => {
      input.disabled = !enabled;
      input.required = enabled && input.name !== 'interior';
    });
  }
  async function refreshQuote() {
    if (controller) controller.abort();
    controller = new AbortController();
    error.textContent = '';
    liveStatus.textContent = 'Actualizando liquidación';
    try {
      const response = await fetch(quoteForm.dataset.quoteUrl, {method:'POST', body:new FormData(quoteForm),
        headers:{'X-CSRFToken':quoteForm.querySelector('[name=csrfmiddlewaretoken]').value}, signal:controller.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'No fue posible actualizar el total.');
      items.replaceChildren();
      for (const item of data.items) {
        const row = document.createElement('div'); row.className = 'amount-row';
        const label = document.createElement('span'); label.textContent = item.label;
        const value = document.createElement('strong'); value.textContent = money.format(Number(item.amount));
        row.append(label,value); items.append(row);
      }
      total.textContent = money.format(Number(data.total)) + ' MXN';
      liveStatus.textContent = 'Total actualizado: ' + total.textContent;
    } catch (e) {
      if (e.name === 'AbortError') return;
      error.textContent = e.message || 'No hay conexión. Puedes confirmar para que el servidor revise tu liquidación.';
      total.textContent = 'Por confirmar';
      liveStatus.textContent = 'No se pudo calcular el total.';
    }
  }
  updateShipping();
  quoteForm.addEventListener('change', event => {
    if (event.target.name === 'delivery') updateShipping();
    if (['delivery','contributions','postal_code'].includes(event.target.name)) {
      clearTimeout(timer); timer = setTimeout(refreshQuote,180);
    }
  });
  quoteForm.querySelector('[name=postal_code]')?.addEventListener('input', () => {
    clearTimeout(timer); timer = setTimeout(refreshQuote,400);
  });
  if (quoteForm.querySelector('[name=delivery]:checked')?.value === 'shipping') refreshQuote();
}
const poll = document.querySelector('#status-poll');
if (poll) {
  let tries = 0;
  const handle = setInterval(async () => {
    if (++tries > 120) {clearInterval(handle); return;}
    if (document.hidden) return;
    try {
      const response = await fetch(poll.dataset.url);
      if (!response.ok) {clearInterval(handle); return;}
      const data = await response.json();
      if (data.status !== poll.dataset.current) window.location.reload();
    } catch (_) { /* La consulta manual sigue disponible al recargar. */ }
  }, 10000);
}
