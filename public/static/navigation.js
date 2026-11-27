document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('navToggle');
    const navigation = document.getElementById('primaryNavigation');
    const compact = window.matchMedia('(max-width: 1100px)');

    function setOpen(open) {
        toggle.setAttribute('aria-expanded', String(open));
        toggle.textContent = open ? 'Close menu' : 'Menu';
        navigation.hidden = compact.matches && !open;
    }

    function updateLayout() {
        const focusInside = navigation.contains(document.activeElement);
        toggle.hidden = !compact.matches;
        setOpen(false);
        if (compact.matches && focusInside) toggle.focus();
    }

    toggle.onclick = () => setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && compact.matches && toggle.getAttribute('aria-expanded') === 'true') {
            setOpen(false);
            toggle.focus();
        }
    });
    navigation.addEventListener('click', event => {
        if (compact.matches && event.target.closest('a, button')) {
            setOpen(false);
            toggle.focus();
        }
    });
    const pending = document.createElement('div');
    pending.className = 'navigation-loading';
    pending.setAttribute('role', 'status');
    pending.hidden = true;
    document.body.append(pending);
    let slowNotice;
    document.addEventListener('click', event => {
        const link = event.target.closest('a[href]');
        if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey ||
            event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
        const destination = new URL(link.href, location.href);
        if (destination.origin !== location.origin || destination.href === location.href ||
            (destination.pathname === location.pathname && destination.search === location.search)) return;
        pending.textContent = 'Loading page…';
        pending.hidden = false;
        clearTimeout(slowNotice);
        slowNotice = setTimeout(() => {
            pending.textContent = 'Still loading. Please wait, or use your browser’s reload button to retry.';
        }, 12000);
    });
    window.addEventListener('pageshow', () => {
        pending.hidden = true;
        clearTimeout(slowNotice);
    });
    compact.addEventListener('change', updateLayout);
    updateLayout();
});
