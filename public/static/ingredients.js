document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('ingredients');
    const numbers = document.getElementById('ingredientNumbers');
    function updateNumbers() {
        numbers.textContent = input.value.split('\n').map((_, index) => `${index + 1}.`).join('\n');
        numbers.scrollTop = input.scrollTop;
    }
    input.addEventListener('keydown', event => {
        if (event.key === 'Enter' && event.shiftKey && !event.isComposing) {
            event.preventDefault();
            const button = document.getElementById('generateBtn');
            if (!event.repeat && !button.disabled) input.form.requestSubmit(button);
        }
    });
    input.addEventListener('input', updateNumbers);
    input.addEventListener('scroll', () => { numbers.scrollTop = input.scrollTop; });
    window.addEventListener('pageshow', updateNumbers);
    updateNumbers();
});
