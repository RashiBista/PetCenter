document.addEventListener('DOMContentLoaded', function () {
  var switcher = document.querySelector('[data-pet-switcher]');
  if (switcher) {
    switcher.addEventListener('change', function () {
      window.location.href = this.value;
    });
  }

  // Photo dropzone (see .photo-dropzone in pet_profile.css) — swaps the
  // preview image the moment a file is picked, since the real
  // <input type="file"> is hidden. Only .photo-dropzone-visual's
  // contents are replaced — the input itself lives outside the
  // <label>, never touched, so the form still submits the selected file.
  var PLACEHOLDER_HTML = '<div class="photo-dropzone-placeholder">'
    + '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="M4 16l4-5 3 3 5-6 4 5"/></svg>'
    + '<span>Upload Photo</span></div>';
  var fileInput = document.querySelector('.photo-dropzone-input');
  var preview = document.querySelector('[data-photo-preview]');
  if (fileInput && preview) {
    fileInput.addEventListener('change', function () {
      var file = this.files && this.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        preview.innerHTML = '<img src="' + e.target.result + '" alt="Selected photo preview">';
      };
      reader.readAsDataURL(file);
    });
  }

  // "Remove current photo" checkbox — reflects the choice immediately
  // in the preview box instead of only taking effect after the form
  // is submitted, and clears out any newly-picked file so the two
  // controls can't contradict each other.
  var clearCheckbox = document.querySelector('.photo-clear-row input[type="checkbox"]');
  if (clearCheckbox && preview) {
    clearCheckbox.addEventListener('change', function () {
      if (this.checked) {
        preview.innerHTML = PLACEHOLDER_HTML;
        if (fileInput) fileInput.value = '';
      }
    });
  }
});