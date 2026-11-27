document.addEventListener('DOMContentLoaded', () => {
    for (const input of document.querySelectorAll('[data-numbered]')) {
    const numbers = input.parentElement.querySelector('.ingredient-numbers');
    function updateNumbers() {
        numbers.textContent = input.value.split('\n').map((_, index) => input.getAttribute('data-numbered') === 'bullets' ? '•' : `${index + 1}.`).join('\n');
        numbers.scrollTop = input.scrollTop;
    }
    input.addEventListener('keydown', event => {
        if (input.id === 'ingredients' && event.key === 'Enter' && event.shiftKey && !event.isComposing) {
            event.preventDefault();
            const button = document.getElementById('generateBtn');
            if (!event.repeat && !button.disabled) input.form.requestSubmit(button);
        }
    });
    input.addEventListener('input', updateNumbers);
    input.addEventListener('scroll', () => { numbers.scrollTop = input.scrollTop; });
    window.addEventListener('pageshow', updateNumbers);
    updateNumbers();
    }
});
