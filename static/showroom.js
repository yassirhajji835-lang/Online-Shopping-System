/* Visual-only enhancements. Checkout, authentication, and inventory remain
   server-side. No external JS libraries and no API calls from this file. */
(() => {
  'use strict';
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Show bundled SVG if an Unsplash photo cannot be loaded (offline, firewall,
  // or an image no longer available). The SVG is already underneath the photo.
  document.querySelectorAll('[data-remote-photo]').forEach(img => {
    const fallback = () => {
      img.style.display = 'none';
      const gallery = img.closest('[data-detail-gallery]');
      if (gallery) {
        gallery.classList.add('illustration-view');
        const photoButton = document.querySelector('[data-gallery-choice="photo"]');
        const illustrationButton = document.querySelector('[data-gallery-choice="illustration"]');
        if (photoButton) {
          photoButton.disabled = true;
          photoButton.title = 'Photo unavailable; showing offline illustration';
          photoButton.classList.remove('active');
          photoButton.setAttribute('aria-pressed', 'false');
        }
        if (illustrationButton) {
          illustrationButton.classList.add('active');
          illustrationButton.setAttribute('aria-pressed', 'true');
        }
      }
    };
    img.addEventListener('error', fallback, { once: true });
    if (img.complete && img.naturalWidth === 0) fallback();
  });

  const gallery = document.querySelector('[data-detail-gallery]');
  if (gallery) {
    document.querySelectorAll('[data-gallery-choice]').forEach(button => {
      button.addEventListener('click', () => {
        const illustration = button.dataset.galleryChoice === 'illustration';
        gallery.classList.toggle('illustration-view', illustration);
        document.querySelectorAll('[data-gallery-choice]').forEach(other => {
          const active = other === button;
          other.classList.toggle('active', active);
          other.setAttribute('aria-pressed', String(active));
        });
      });
    });
  }

  if (reducedMotion) return;
  if ('IntersectionObserver' in window) {
    document.documentElement.classList.add('js-motion');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.07, rootMargin: '0px 0px 70px 0px' });
    document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));
  }

  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

  const stage = document.querySelector('[data-hero-stage]');
  if (stage) {
    let frame = 0;
    stage.addEventListener('pointermove', e => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const r = stage.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        stage.style.setProperty('--move-x', `${(x * 14).toFixed(1)}px`);
        stage.style.setProperty('--move-y', `${(y * 12).toFixed(1)}px`);
        stage.style.setProperty('--move-x2', `${(x * -17).toFixed(1)}px`);
        stage.style.setProperty('--move-y2', `${(y * -14).toFixed(1)}px`);
      });
    }, { passive: true });
    stage.addEventListener('pointerleave', () => {
      stage.style.setProperty('--move-x', '0px');
      stage.style.setProperty('--move-y', '0px');
      stage.style.setProperty('--move-x2', '0px');
      stage.style.setProperty('--move-y2', '0px');
    });
  }

  document.querySelectorAll('[data-tilt-card]').forEach(card => {
    let frame = 0;
    card.addEventListener('pointermove', e => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        card.style.setProperty('--ry', `${(x * 3.5).toFixed(2)}deg`);
        card.style.setProperty('--rx', `${(-y * 3.5).toFixed(2)}deg`);
      });
    }, { passive: true });
    card.addEventListener('pointerleave', () => {
      card.style.setProperty('--ry', '0deg');
      card.style.setProperty('--rx', '0deg');
    });
  });
})();
