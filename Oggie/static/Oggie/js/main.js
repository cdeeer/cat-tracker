// PawTrack — Main JS

document.addEventListener('DOMContentLoaded', function () {

  // Quick-amount buttons on donation page
  document.querySelectorAll('.btn-amount').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.btn-amount').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      const amountInput = document.querySelector('[name="amount"]');
      if (amountInput) {
        amountInput.value = this.dataset.amount;
      }
    });
  });

  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll('.paw-alert').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 5000);
  });

  // Highlight active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll('.pawtrack-nav .nav-link').forEach(function (link) {
    if (link.getAttribute('href') === currentPath) {
      link.style.background = 'var(--cream-dark)';
      link.style.color = 'var(--orange)';
    }
  });

  // Image preview on cat report form
  const photoInput = document.querySelector('input[name="photo"]');
  if (photoInput) {
    photoInput.addEventListener('change', function () {
      const file = this.files[0];
      if (!file) return;
      const existing = document.getElementById('photo-preview');
      if (existing) existing.remove();
      const reader = new FileReader();
      reader.onload = function (e) {
        const img = document.createElement('img');
        img.id = 'photo-preview';
        img.src = e.target.result;
        img.style.cssText = 'width:120px;height:90px;object-fit:cover;border-radius:12px;border:2px solid var(--brown);margin-top:0.5rem;display:block';
        photoInput.insertAdjacentElement('afterend', img);
      };
      reader.readAsDataURL(file);
    });
  }

  // Paw print cursor sparkle effect on hover of cat cards
  document.querySelectorAll('.cat-card').forEach(function (card) {
    card.addEventListener('mouseenter', function () {
      this.style.cursor = 'pointer';
    });
  });

});
