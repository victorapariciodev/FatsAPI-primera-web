/* Modal de la seccion Stream HUD.

Los videos YA vienen renderizados por el servidor con URL validada: este
archivo solo abre y cierra el <dialog> correspondiente. No hay fetch, no hay
construccion de src en el cliente y no hay estado que sincronizar.
 */

(() => {
  document.addEventListener('click', (event) => {
    const abrir = event.target.closest('[data-video-open]');
    if (abrir) {
      const dialog = document.getElementById(abrir.dataset.videoOpen);
      if (dialog && typeof dialog.showModal === 'function') dialog.showModal();
      return;
    }

    const cerrar = event.target.closest('[data-video-close]');
    if (cerrar) {
      const dialog = cerrar.closest('dialog');
      if (dialog) dialog.close();
      return;
    }

    // Clic en el fondo oscuro del dialog (backdrop) tambien cierra.
    if (event.target instanceof HTMLDialogElement && event.target.hasAttribute('data-video-dialog')) {
      event.target.close();
    }
  });
})();
