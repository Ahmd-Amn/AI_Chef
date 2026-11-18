document.addEventListener('DOMContentLoaded', () => {
    const $ = (id) => document.getElementById(id);
    let csrf = document.querySelector('meta[name="csrf-token"]').content;
    let loggedIn = $('authBtn').textContent.includes('Log out');
    let currentRecipe = null;
    let registering = false;

    async function api(path, options = {}) {
        const response = await fetch(path, {
            ...options,
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...options.headers }
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Something went wrong.');
        return data;
    }

    function showRecipe(data) {
        currentRecipe = data;
        if (!window.marked || !window.DOMPurify) throw new Error('Recipe viewer could not load. Refresh the page.');
        $('recipeContent').innerHTML = DOMPurify.sanitize(marked.parse(data.recipe));
        $('favoriteBtn').textContent = data.favorite ? 'Remove from favorites' : 'Add to favorites';
        $('favoriteBtn').hidden = !loggedIn || !data.id;
        $('previewArt').classList.add('hidden');
        $('recipePreview').classList.add('has-recipe');
        $('recipeContainer').classList.remove('hidden');
        $('recipeContainer').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    }

    function showAuth() {
        $('authPanel').showModal();
        $('email').focus();
    }
    $('authClose').addEventListener('click', () => $('authPanel').close());

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
        $('authError').textContent = '';
        try {
            const data = await api(registering ? '/auth/register' : '/auth/login', {
                method: 'POST', body: JSON.stringify({ email: $('email').value, password: $('password').value })
            });
            csrf = data.csrf_token;
            location.reload();
        } catch (error) { $('authError').textContent = error.message; }
    });

    $('recipeForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        const ingredients = $('ingredients').value.trim();
        if (!ingredients) return $('ingredients').focus();
        $('recipeContainer').classList.add('hidden');
        $('errorContainer').classList.add('hidden');
        $('loading').classList.remove('hidden');
        $('generateBtn').disabled = true;
        $('generateBtn').textContent = 'Making your recipe…';
        try {
            showRecipe(await api('/api/recipe', { method: 'POST', body: JSON.stringify({ ingredients }) }));
        } catch (error) {
            $('errorContent').textContent = error.message;
            $('errorContainer').classList.remove('hidden');
        } finally {
            $('loading').classList.add('hidden');
            $('generateBtn').disabled = false;
            $('generateBtn').innerHTML = 'Get a recipe <span aria-hidden="true">↗</span>';
        }
    });

    $('favoriteBtn').addEventListener('click', async () => {
        if (!currentRecipe) return;
        if (!loggedIn) return showAuth();
        try {
            const favorite = !currentRecipe.favorite;
            await api(`/api/recipes/${currentRecipe.id}/favorite`, { method: favorite ? 'POST' : 'DELETE' });
            currentRecipe.favorite = favorite;
            $('favoriteBtn').textContent = favorite ? 'Remove from favorites' : 'Add to favorites';
        } catch (error) { alert(error.message); }
    });

    async function openLibrary(favorites) {
        if (!loggedIn) return showAuth();
        try {
            const data = await api(favorites ? '/api/favorites' : '/api/recipes');
            $('libraryTitle').textContent = favorites ? 'Favorites' : 'Recipe history';
            $('recipeList').replaceChildren();
            if (!data.recipes.length) $('recipeList').textContent = favorites ? 'No favorites yet.' : 'No recipes yet.';
            for (const recipe of data.recipes) {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'recipe-row';
                button.textContent = `${recipe.title} · ${recipe.ingredients} · ${recipe.created_at}${recipe.favorite ? ' ♥' : ''}`;
                button.addEventListener('click', async () => {
                    try {
                        const data = await api(`/api/recipes/${recipe.id}`);
                        $('library').close();
                        showRecipe(data);
                    }
                    catch (error) { alert(error.message); }
                });
                $('recipeList').append(button);
            }
            $('library').showModal();
        } catch (error) { alert(error.message); }
    }
    $('historyBtn').addEventListener('click', () => openLibrary(false));
    $('favoritesBtn').addEventListener('click', () => openLibrary(true));
    $('closeLibrary').addEventListener('click', () => $('library').close());
});
