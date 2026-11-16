/* NightKids store: capa minima de interaccion contra /api/*.
 *
 * Regla del contrato: el front NO calcula dinero ni inventa estado. Recibe
 * montos como string ya calculados por el backend y se limita a pintar.
 */
window.NK = window.NK || {};

(function () {
  function mensajeDeError(payload, status) {
    if (!payload) return 'No se pudo completar la operacion (HTTP ' + status + ')';
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg || 'dato invalido').join(' · ');
    }
    if (typeof payload.detail === 'string') return payload.detail;
    if (typeof payload.message === 'string') return payload.message;
    return 'No se pudo completar la operacion (HTTP ' + status + ')';
  }

  NK.request = async function (url, method, body) {
    const options = { method: method || 'GET', headers: { Accept: 'application/json' } };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }

    if (!response.ok) {
      const failure = new Error(mensajeDeError(payload, response.status));
      failure.status = response.status;
      failure.code = payload && payload.code;
      throw failure;
    }

    return payload;
  };

  NK.setCartCount = function (total) {
    window.NK.cartCount = total;
    const badge = document.querySelector('a[href="/carrito"] span.bg-primary-container');
    if (!badge) return;

    if (total > 0) {
      badge.textContent = total;
    } else {
      badge.remove();
    }
  };

  NK.addToCart = async function (variantId, quantity) {
    const carrito = await NK.request('/api/cart/items', 'POST', {
      variant_id: variantId,
      quantity: quantity,
    });
    NK.setCartCount(carrito.total_items);
    return carrito;
  };
})();

// Reloj de la franja de telemetria. Cosmetico, pero coherente con el diseno.
(function () {
  const clock = document.getElementById('telemetry-clock');
  if (!clock) return;

  const render = () => {
    const now = new Date();
    clock.textContent = now.toTimeString().slice(0, 8);
  };

  render();
  setInterval(render, 1000);
})();
