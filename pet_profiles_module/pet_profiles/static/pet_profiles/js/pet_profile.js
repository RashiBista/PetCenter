document.addEventListener("DOMContentLoaded", () => {
    const switcher = document.querySelector("[data-pet-switcher]");
    if (switcher) {
        switcher.addEventListener("change", (event) => {
            window.location.href = event.target.value;
        });
    }

    const photoInput = document.querySelector('input[type="file"][name="photo"]');
    const preview = document.querySelector("[data-photo-preview]");
    if (photoInput && preview) {
        photoInput.addEventListener("change", () => {
            const [file] = photoInput.files;
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                preview.innerHTML = `<img src="${event.target.result}" alt="Selected pet photo preview">`;
            };
            reader.readAsDataURL(file);
        });
    }

    window.setTimeout(() => {
        document.querySelectorAll(".message").forEach((message) => {
            message.classList.add("message-hidden");
        });
    }, 4000);
});
