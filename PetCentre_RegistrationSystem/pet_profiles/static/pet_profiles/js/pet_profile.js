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
  // contents are replaced — the input itself is a sibling, never
  // touched, so the form still submits the selected file.
  var fileInput = document.querySelector('.photo-dropzone input[type="file"]');
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
});