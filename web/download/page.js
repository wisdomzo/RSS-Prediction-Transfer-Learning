(function () {
  'use strict';
  const menu = document.querySelector('.menu-toggle');
  const nav = document.getElementById('main-nav');
  function closeMenu() {
    menu.setAttribute('aria-expanded', 'false');
    nav.classList.remove('is-open');
  }
  menu.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  });
  nav.addEventListener('click', (event) => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && nav.classList.contains('is-open')) { closeMenu(); menu.focus(); }
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.site-header')) closeMenu();
  });

  const passwordDialog = document.getElementById('download-password-dialog');
  const passwordForm = document.getElementById('download-password-form');
  const passwordInput = document.getElementById('download-password');
  const passwordError = document.getElementById('password-error');
  let pendingDownload = null;
  function clearPassword() {
    passwordForm.reset();
    passwordError.hidden = true;
    passwordInput.removeAttribute('aria-invalid');
  }
  document.getElementById('password-cancel').addEventListener('click', () => passwordDialog.close());
  passwordDialog.addEventListener('close', () => { pendingDownload = null; clearPassword(); });
  passwordInput.addEventListener('input', () => {
    passwordError.hidden = true;
    passwordInput.removeAttribute('aria-invalid');
  });
  passwordForm.addEventListener('submit', (event) => {
    event.preventDefault();
    if (passwordInput.value !== 'asset') {
      passwordError.hidden = false;
      passwordInput.setAttribute('aria-invalid', 'true');
      passwordInput.focus();
      passwordInput.select();
      return;
    }
    const destination = pendingDownload;
    passwordDialog.close();
    if (destination) window.location.assign(destination);
  });

  let available = 0;
  for (const row of document.querySelectorAll('[data-release]')) {
    const release = (window.ASSET_RELEASES || {})[row.dataset.release];
    if (!release || typeof release.url !== 'string' || !release.url.trim()) continue;
    // Only trusted web or relative links; never allow executable URL schemes.
    let url;
    try { url = new URL(release.url, location.href); } catch (_) { continue; }
    const relativeFile = location.protocol === 'file:' && url.protocol === 'file:';
    if (!['https:', 'http:'].includes(url.protocol) && !relativeFile) continue;
    const anchor = row.querySelector('.release-download');
    anchor.href = '#download-password-dialog';
    anchor.setAttribute('aria-haspopup', 'dialog');
    anchor.addEventListener('click', (event) => {
      event.preventDefault();
      clearPassword();
      pendingDownload = url.href;
      passwordDialog.showModal();
      passwordInput.focus();
    });
    anchor.hidden = false;
    anchor.setAttribute('aria-label', row.querySelector('h3').textContent + ' ダウンロード / Download');
    row.querySelector('.release-pending').hidden = true;
    if (release.version) {
      const version = row.querySelector('.release-version');
      version.textContent = String(release.version);
      version.hidden = false;
    }
    available++;
  }
  if (available) document.querySelector('.downloads .compact > p').textContent = '公開中 / Available';
})();
