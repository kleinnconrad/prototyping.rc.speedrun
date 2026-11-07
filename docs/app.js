document.addEventListener('DOMContentLoaded', () => {
    showErrorIfDrawingMissing();
});

// Shows the error message instead of the drawing if latest_setup_drawing.svg cannot be loaded.
function showErrorIfDrawingMissing() {
    const drawing = document.getElementById('setup-drawing');
    const showError = () => {
        document.getElementById('drawing-info').style.display = 'none';
        document.getElementById('error').style.display = 'flex';
    };
    drawing.addEventListener('error', showError);
    if (drawing.complete && drawing.naturalWidth === 0) {
        showError();
    }
}
