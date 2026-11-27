document.addEventListener('DOMContentLoaded', () => {
    const $ = (id) => document.getElementById(id);
    let csrf = document.querySelector('meta[name="csrf-token"]').content;
    let loggedIn = $('authBtn').dataset.loggedIn === 'true';
    let currentRecipe = null;
    let registering = false;

    async function api(path, options = {}) {
        let response;
        try { response = await fetch(path, {
            ...options,
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...options.headers }
        }); } catch { throw new Error('No services are available right now. Please try again later.'); }
        if (!response.headers.get('content-type')?.includes('application/json')) {
            throw new Error('No services are available right now. Please try again later.');
        }
        const data = await response.json();
        if (!response.ok) {
            if (data.fields) window.showFieldErrors(data.fields);
            throw new Error(response.status >= 500 && !data.retry_after ? 'No services are available right now. Please try again later.' : data.error || 'Please check your entries.');
        }
        return data;
    }

    function showRecipe(data) {
        $('startCooking').hidden = !data.steps?.length;
        if (!window.marked || !window.DOMPurify) throw new Error('Recipe viewer could not load. Refresh the page.');
        const rendered = DOMPurify.sanitize(marked.parse(data.recipe));
        currentRecipe = data;
        $('recipeContent').innerHTML = rendered;
        $('favoriteBtn').setAttribute('aria-pressed', String(Boolean(data.favorite)));
        $('favoriteBtn').textContent = data.favorite ? 'Remove from favorites' : 'Add to favorites';
        $('favoriteBtn').hidden = !loggedIn || !data.id;
        $('previewArt').classList.add('hidden');
        $('recipePreview').classList.add('has-recipe');
        $('recipeContainer').classList.remove('hidden');
        $('recipeContainer').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    }

    $('startCooking').onclick = () => document.dispatchEvent(new CustomEvent('cooking:start', {detail: currentRecipe}));

    function showAuth() {
        $('authPanel').showModal();
        $('email').focus();
    }
    $('authClose').addEventListener('click', () => $('authPanel').close());
    $('showPassword').addEventListener('click', () => {
        const visible = $('password').type === 'password';
        $('password').type = visible ? 'text' : 'password';
        $('showPassword').textContent = visible ? 'Hide' : 'Show';
        $('showPassword').setAttribute('aria-label', `${visible ? 'Hide' : 'Show'} password`);
        $('showPassword').setAttribute('aria-pressed', String(visible));
    });

    $('authBtn').addEventListener('click', async () => {
        if (!loggedIn) return showAuth();
        try {
            await api('/auth/logout', { method: 'POST' });
            location.reload();
        } catch (error) { alert(error.message); }
    });

    $('authSwitch').addEventListener('click', () => {
        registering = !registering;
        $('authTitle').textContent = registering ? 'Create an account' : 'Log in';
        $('authSubmit').textContent = registering ? 'Create account' : 'Log in';
        $('authSwitch').textContent = registering ? 'Log in instead' : 'Create an account';
        $('password').autocomplete = registering ? 'new-password' : 'current-password';
        $('authError').textContent = '';
    });

    $('authForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        if ($('authSubmit').disabled) return;
        $('authError').textContent = '';
        $('authSubmit').disabled = true;
        $('authSwitch').disabled = true;
        $('authSubmit').classList.add('circle-loading');
        $('authSubmit').textContent = registering ? 'Creating… wait a moment' : 'Logging in…';
        try {
            const data = await api(registering ? '/auth/register' : '/auth/login', {
                method: 'POST', body: JSON.stringify({ email: $('email').value, password: $('password').value })
            });
            csrf = data.csrf_token;
            location.reload();
        } catch (error) {
            $('authError').textContent = error.message;
            window.focusSubmissionError($('authError'));
        }
        finally {
            $('authSubmit').disabled = false;
            $('authSwitch').disabled = false;
            $('authSubmit').classList.remove('circle-loading');
            $('authSubmit').textContent = registering ? 'Create account' : 'Log in';
        }
    });

    $('recipeForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        const ingredients = $('ingredients').value.trim();
        if (!ingredients) return $('ingredients').focus();
        $('errorContainer').classList.add('hidden');
        $('loading').classList.remove('hidden');
        $('generateBtn').disabled = true;
        $('generateBtn').textContent = 'Making your recipe…';
        try {
            showRecipe(await api('/api/recipe', { method: 'POST', body: JSON.stringify({ ingredients }) }));
        } catch (error) {
            $('errorContent').textContent = error.message;
            $('errorContainer').classList.remove('hidden');
            window.focusSubmissionError($('errorContainer'));
        } finally {
            $('loading').classList.add('hidden');
            $('generateBtn').disabled = false;
            $('generateBtn').innerHTML = 'Get a recipe <span aria-hidden="true"></span>';
        }
    });

    $('favoriteBtn').addEventListener('click', async () => {
        if (!currentRecipe) return;
        if (!loggedIn) return showAuth();
        try {
            const favorite = !currentRecipe.favorite;
            await api(`/api/recipes/${currentRecipe.id}/favorite`, { method: favorite ? 'POST' : 'DELETE' });
            currentRecipe.favorite = favorite;
            $('favoriteBtn').setAttribute('aria-pressed', String(favorite));
            $('favoriteBtn').textContent = favorite ? 'Remove from favorites' : 'Add to favorites';
            if (!favorite) window.showRemoved();
        } catch (error) { alert(error.message); }
    });

    document.addEventListener('recipe:selected', event => showRecipe(event.detail));
});
