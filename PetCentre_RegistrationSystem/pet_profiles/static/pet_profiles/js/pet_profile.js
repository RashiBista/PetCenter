document.addEventListener('DOMContentLoaded', function () {
  var switcher = document.querySelector('[data-pet-switcher]');
  if (switcher) {
    switcher.addEventListener('change', function () {
      window.location.href = this.value;
    });
  }

  // Custom file picker (see .file-picker in pet_profile.css) — keeps the
  // filename readout and the circular preview in sync with whatever the
  // user actually picked, since the real <input type="file"> is hidden.
  var fileInput = document.querySelector('.file-picker input[type="file"]');
  var fileNameEl = document.querySelector('[data-file-name]');
  var preview = document.querySelector('[data-photo-preview]');
  if (fileInput && fileNameEl) {
    fileInput.addEventListener('change', function () {
      var file = this.files && this.files[0];
      fileNameEl.textContent = file ? file.name : 'No file chosen';
      if (file && preview) {
        var reader = new FileReader();
        reader.onload = function (e) {
          preview.innerHTML = '<img src="' + e.target.result + '" alt="Selected photo preview">';
        };
        reader.readAsDataURL(file);
      }
    });
  }
});