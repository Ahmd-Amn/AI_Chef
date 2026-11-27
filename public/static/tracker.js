document.addEventListener('DOMContentLoaded', () => {
    const saved = document.getElementById('savedPopup');
    const savedEntry = /^#food-log-\d+$/.test(location.hash) ? document.getElementById(location.hash.slice(1)) : null;
    function showSavedEntry() {
        if (!savedEntry) return;
        savedEntry.scrollIntoView({
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
            block:'start'
        });
        if (!saved?.open) savedEntry.focus({preventScroll:true});
    }
    if (saved) {
        saved.showModal();
        saved.addEventListener('close', showSavedEntry);
    }
    if (savedEntry) {
        if (document.readyState === 'complete') showSavedEntry();
        else window.addEventListener('load', showSavedEntry, {once:true});
    }
    const estimate = document.getElementById('nutritionEstimate');
    if (estimate && !document.querySelector('[role="alert"]')) {
        function showEstimate() {
            document.getElementById('estimateHeading').focus({preventScroll:true});
            estimate.scrollIntoView({
                behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
                block:'start'
            });
        }
        if (document.readyState === 'complete') showEstimate();
        else window.addEventListener('load', showEstimate, {once:true});
    }
    const form = document.querySelector('.meal-form');
    const button = form.querySelector('[value="estimate"]');
    const calculating = document.getElementById('calculatingPopup');
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
        calculating.showModal();
    });
    window.addEventListener('pageshow', () => {
        form.removeAttribute('aria-busy');
        button.disabled = false;
        button.textContent = 'Estimate nutrition';
        form.querySelectorAll('input[name="action"]').forEach(input => input.remove());
        if (calculating.open) calculating.close();
    });
});
