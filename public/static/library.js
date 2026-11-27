document.addEventListener('DOMContentLoaded', () => {
    const dialog = document.getElementById('library');
    const list = document.getElementById('recipeList');
    const detail = document.getElementById('libraryDetail');
    let current;
    const status = document.getElementById('libraryStatus');

    async function get(path) {
        const response = await fetch(path);
        if (!response.ok) throw new Error(response.status === 401 ? 'Please log in to view your recipes.' : 'Could not load recipes. Please try again.');
        return response.json();
    }

    async function openLibrary(favorites) {
        if (document.getElementById('authPanel') && document.getElementById('authBtn').textContent.includes('Log in')) {
            document.getElementById('authPanel').showModal();
            return;
        }
        document.getElementById('libraryTitle').textContent = favorites ? 'Favorites' : 'Recipe history';
        detail.hidden = true;
        list.hidden = false;
        list.replaceChildren();
        status.textContent = 'Loading recipes…';
        dialog.showModal();
        try {
            const data = await get(favorites ? '/api/favorites' : '/api/recipes');
            status.textContent = data.recipes.length ? '' : (favorites ? 'No favorites yet.' : 'No recipes yet.');
            for (const recipe of data.recipes) {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'recipe-row';
                const title = document.createElement('strong');
                title.className = 'recipe-row-title';
                title.textContent = recipe.title;
                const ingredients = document.createElement('span');
                ingredients.className = 'recipe-row-ingredients';
                ingredients.textContent = recipe.ingredients;
                button.append(title, ingredients);
                button.onclick = async () => {
                    button.disabled = true;
                    status.textContent = 'Loading recipe…';
                    try {
                        const selected = await get(`/api/recipes/${recipe.id}`);
                        status.textContent = '';
                        if (!window.marked || !window.DOMPurify) throw new Error('Recipe viewer could not load. Please refresh and try again.');
                        current = selected;
                        list.hidden = true;
                        detail.hidden = false;
                        document.getElementById('libraryRecipe').innerHTML = DOMPurify.sanitize(marked.parse(selected.recipe));
                        document.getElementById('libraryFavorite').textContent = selected.favorite ? 'Remove from favorites' : 'Add to favorites';
                        document.getElementById('libraryCooking').hidden = !selected.steps?.length;
                        document.getElementById('libraryBack').focus();
                    } catch (error) {
                        status.textContent = error.message;
                    } finally {
                        button.disabled = false;
                    }
                };
                list.append(button);
            }
        } catch (error) {
            status.textContent = error.message;
        }
    }

    document.getElementById('libraryCooking').onclick = () => {
        document.dispatchEvent(new CustomEvent('cooking:start', {detail: current}));
    };
    document.getElementById('libraryFavorite').onclick = async event => {
        const button = event.currentTarget;
        button.disabled = true;
        try {
            const response = await fetch(`/api/recipes/${current.id}/favorite`, {
                method: current.favorite ? 'DELETE' : 'POST',
                headers: {'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content}
            });
            if (!response.ok) throw new Error('Could not update favorite. Please try again.');
            current.favorite = !current.favorite;
            button.textContent = current.favorite ? 'Remove from favorites' : 'Add to favorites';
        } catch (error) { status.textContent = error.message; }
        finally { button.disabled = false; }
    };

    for (const [id, favorites] of [['historyBtn', false], ['favoritesBtn', true]]) {
        document.getElementById(id).onclick = event => {
            event.preventDefault();
            openLibrary(favorites);
        };
    }
    document.getElementById('closeLibrary').onclick = () => dialog.close();
    document.getElementById('libraryBack').onclick = () => {
        detail.hidden = true;
        list.hidden = false;
        list.querySelector('button')?.focus();
    };
    const requested = new URLSearchParams(location.search).get('library');
    if (requested === 'history' || requested === 'favorites') openLibrary(requested === 'favorites');
});
