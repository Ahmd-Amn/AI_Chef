document.addEventListener('DOMContentLoaded', () => {
    const savedPopup = document.getElementById('planSavedPopup');
    if (savedPopup) {
        savedPopup.showModal();
        savedPopup.addEventListener('close', () => {
            const entry = document.getElementById(savedPopup.dataset.savedPlan);
            if (!entry) return;
            entry.focus({preventScroll:true});
            entry.scrollIntoView({
                behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
                block:'start'
            });
        });
    }
    const form = document.querySelector('.planner-form');
    const button = form.querySelector('[value="generate"]');
    const popup = document.getElementById('planningPopup');
    form.addEventListener('submit', event => {
        if (form.getAttribute('aria-busy') === 'true') {
            event.preventDefault();
            return;
        }
        const action = document.createElement('input');
        action.type = 'hidden';
        action.name = 'action';
        action.value = 'generate';
        form.append(action);
        button.disabled = true;
        form.setAttribute('aria-busy', 'true');
        popup.showModal();
    });
    window.addEventListener('pageshow', () => {
        form.removeAttribute('aria-busy');
        button.disabled = false;
        form.querySelectorAll('input[name="action"]').forEach(input => input.remove());
        if (popup.open) popup.close();
    });
    const result = document.getElementById('planResult');
    if (result && (location.hash === '#planResult' || result.hasAttribute('data-scroll-result'))) {
        function showPlan() {
            document.getElementById('planResultHeading').focus({preventScroll:true});
            result.scrollIntoView({
                behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
                block:'start'
            });
        }
        if (document.readyState === 'complete') showPlan();
        else window.addEventListener('load', showPlan, {once:true});
    }
});
