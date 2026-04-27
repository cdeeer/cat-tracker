/**
 * Replace a broken <img> (404/deleted-from-disk) with the animated emoji
 * placeholder. The replacement tile inherits the <img>'s classes and inline
 * styles so it drops into lists, cards, and thumbnails without extra CSS.
 *
 * Usage: <img ... onerror="oggieCatPhotoFallback(this)">
 *
 * Also runs automatically on DOMContentLoaded for any <img.cat-photo-fallback>
 * that failed during page load before this script executed.
 */
(function (global) {
  function isSmall(img) {
    // Heuristic: thumbnails explicitly size themselves inline (width:48px etc.)
    // and don't use one of the big card classes.
    if (img.classList.contains('cat-photo') || img.classList.contains('cat-photo-lg')) {
      return false;
    }
    return true;
  }

  function fallback(img) {
    if (!img || img.dataset.oggieFallback === '1') return;
    img.dataset.oggieFallback = '1';

    const placeholder = document.createElement('div');
    // Carry over the img's classes so sizing/shape rules still apply.
    placeholder.className = img.className;
    // Add the emoji classes — big tile when <img> used a full-size class,
    // otherwise the small inline variant.
    if (isSmall(img)) {
      placeholder.classList.add('cat-photo-emoji-sm');
    } else {
      placeholder.classList.add('cat-photo-emoji');
    }
    // Preserve inline dimensions/border-radius from the original <img>.
    if (img.getAttribute('style')) {
      placeholder.setAttribute('style', img.getAttribute('style'));
    }
    placeholder.setAttribute('aria-label', 'Photo missing — placeholder');

    const glyph = document.createElement('span');
    glyph.className = 'cat-glyph';
    glyph.textContent = '😼';
    placeholder.appendChild(glyph);

    img.parentNode.replaceChild(placeholder, img);
  }

  global.oggieCatPhotoFallback = fallback;

  // Catch imgs that already failed before this script loaded.
  function sweep() {
    document.querySelectorAll('img[data-cat-photo]').forEach(function (img) {
      if (img.complete && img.naturalWidth === 0) fallback(img);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', sweep);
  } else {
    sweep();
  }
})(window);
