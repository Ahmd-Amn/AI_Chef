document.addEventListener('DOMContentLoaded', () => {
    window.showRemoved = () => {
        const x = window.scrollX, y = window.scrollY;
        document.getElementById('removedPopup').showModal();
        window.scrollTo({left:x, top:y, behavior:'instant'});
    };
    document.addEventListener('submit', event => {
        if (!['delete', 'delete_custom'].includes(event.submitter?.value)) return;
        try {
            sessionStorage.setItem('removalPosition', JSON.stringify({path:location.pathname, x:window.scrollX, y:window.scrollY}));
        } catch {}
    });
    if (document.getElementById('removedPopup')?.hasAttribute('data-removed')) {
        window.addEventListener('load', () => {
            window.showRemoved();
            try {
                const position = JSON.parse(sessionStorage.getItem('removalPosition'));
                sessionStorage.removeItem('removalPosition');
                if (position?.path === location.pathname) {
                    window.scrollTo({left:position.x, top:position.y, behavior:'instant'});
                }
            } catch {}
        }, {once:true});
    }
    window.focusSubmissionError = element => {
        if (!element) return;
        if (element.tabIndex < 0 && !element.hasAttribute('tabindex')) element.setAttribute('tabindex', '-1');
        element.focus({preventScroll:true});
        element.scrollIntoView({
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
            block:'center'
        });
    };
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
        window.focusSubmissionError(first);
    };
    document.addEventListener('invalid', event => {
        const field = event.target;
        const name = field.name || field.id;
        if (name) {
            const message = document.documentElement.lang === 'ms'
                ? (field.validity.valueMissing ? 'Sila isi ruangan ini.' : 'Sila semak format atau nilai dalam ruangan ini.')
                : field.validationMessage;
            window.showFieldErrors({[name]: message});
        }
    }, true);
    document.addEventListener('input', event => {
        const field = event.target;
        field.removeAttribute('aria-invalid');
        const note = document.getElementById(`error-${field.name || field.id}`);
        if (note) note.textContent = '';
    });
    const errors = document.getElementById('fieldErrors');
    if (errors) window.showFieldErrors(JSON.parse(errors.textContent));
    else {
        const message = document.querySelector('[role="alert"]');
        if (message?.textContent.trim()) window.focusSubmissionError(message);
    }

    for (const form of document.querySelectorAll('.estimate-review, .date-filter')) {
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
