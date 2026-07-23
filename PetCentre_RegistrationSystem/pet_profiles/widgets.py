from django import forms


class DropzoneClearableFileInput(forms.ClearableFileInput):
    """
    ClearableFileInput's built-in template renders "Currently: <a>...</a>
    [checkbox] Clear<br>Change: <input>" as one inline blob with no CSS
    hooks to separate the pieces — that's what was bleeding out from
    inside the styled .photo-dropzone box. This override keeps the same
    clear-checkbox behavior (still read by Django's own
    ClearableFileInput.value_from_datadict) but renders clean, minimal
    markup that the template can position independently: the file input
    stays hidden inside the dropzone, the "Remove current photo" row
    renders separately below it.
    """
    template_name = "pet_profiles/widgets/photo_input.html"
