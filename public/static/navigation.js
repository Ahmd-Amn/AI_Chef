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
    compact.addEventListener('change', updateLayout);
    updateLayout();
});
