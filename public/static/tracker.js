document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.meal-form');
    const button = form.querySelector('[value="estimate"]');
    const status = document.getElementById('estimateStatus');
    form.addEventListener('submit', event => {
        if (form.getAttribute('aria-busy') === 'true') {
            event.preventDefault();
            return;
        }
        const action = document.createElement('input');
        action.type = 'hidden';
        action.name = 'action';
        action.value = 'estimate';
        form.append(action);
        button.disabled = true;
        button.textContent = 'Estimating nutrition…';
        form.setAttribute('aria-busy', 'true');
        status.textContent = 'Estimating your meal. Please wait.';
    });
    window.addEventListener('pageshow', () => {
        form.removeAttribute('aria-busy');
        button.disabled = false;
        button.textContent = 'Estimate nutrition';
        form.querySelectorAll('input[name="action"]').forEach(input => input.remove());
        status.textContent = '';
    });
});
