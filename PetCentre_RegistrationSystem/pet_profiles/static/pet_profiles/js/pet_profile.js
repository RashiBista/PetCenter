document.addEventListener('DOMContentLoaded', function () {
  var switcher = document.querySelector('[data-pet-switcher]');
  if (switcher) {
    switcher.addEventListener('change', function () {
      window.location.href = this.value;
    });
  }
});