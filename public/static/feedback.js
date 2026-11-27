document.addEventListener('DOMContentLoaded', () => {
    window.showFieldErrors = errors => {
        let first;
        for (const [name, message] of Object.entries(errors)) {
            const field = document.querySelector(`.estimate-review [name="${name}"]`) || document.querySelector(`[name="${name}"], #${name}`);
            if (!field) continue;
            const id = `error-${name}`;
            let note = document.getElementById(id);
            if (!note) {
                note = document.createElement('span');
                note.id = id;
                note.className = 'field-error';
                field.insertAdjacentElement('afterend', note);
            }
            note.textContent = message;
            field.setAttribute('aria-invalid', 'true');
            const descriptions = new Set((field.getAttribute('aria-describedby') || '').split(' ').filter(Boolean));
            descriptions.add(id);
            field.setAttribute('aria-describedby', [...descriptions].join(' '));
            field.closest('details')?.setAttribute('open', '');
            first ||= field;
        }
        first?.focus();
    };
    document.addEventListener('invalid', event => {
        const field = event.target;
        const name = field.name || field.id;
        if (name) window.showFieldErrors({[name]: field.validationMessage});
    }, true);
    document.addEventListener('input', event => {
        const field = event.target;
        field.removeAttribute('aria-invalid');
        const note = document.getElementById(`error-${field.name || field.id}`);
        if (note) note.textContent = '';
    });
    const errors = document.getElementById('fieldErrors');
    if (errors) window.showFieldErrors(JSON.parse(errors.textContent));

    const pageSkeleton = document.querySelector('.page-skeleton');
    if (pageSkeleton && document.readyState !== 'complete') {
        pageSkeleton.hidden = false;
        window.addEventListener('load', () => { pageSkeleton.hidden = true; }, {once:true});
        setTimeout(() => { pageSkeleton.hidden = true; }, 4000);
    }
    for (const form of document.querySelectorAll('.planner-form, .estimate-review, .date-filter')) {
        form.addEventListener('submit', event => {
            if (form.dataset.pending) { event.preventDefault(); return; }
            form.dataset.pending = 'true';
            form.setAttribute('aria-busy', 'true');
            const pending = document.createElement('div');
            pending.className = 'skeleton submit-skeleton';
            pending.setAttribute('role', 'status');
            pending.textContent = 'Please wait…';
            for (let i=0; i<3; i++) pending.append(document.createElement('span'));
            form.append(pending);
        });
    }
    window.addEventListener('pageshow', () => {
        document.querySelectorAll('[data-pending]').forEach(form => {
            delete form.dataset.pending;
            form.removeAttribute('aria-busy');
            form.querySelector('.submit-skeleton')?.remove();
        });
    });
});
