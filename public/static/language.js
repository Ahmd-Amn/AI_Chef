document.addEventListener('DOMContentLoaded', async () => {
    const selector = document.getElementById('language');
    let language = 'en';
    try { language = localStorage.getItem('language') === 'ms' ? 'ms' : 'en'; } catch {}
    let dictionary;
    try {
        const response = await fetch('/static/ms.json');
        if (!response.ok) throw new Error();
        dictionary = await response.json();
    } catch {
        selector.disabled = true;
        selector.title = 'Language options could not load. Please reload.';
        return;
    }
    const originals = new WeakMap();
    const attributes = new WeakMap();
    const protectedSelector = 'script,style,textarea,[data-user-content],#recipeContent,#libraryRecipe,#instruction,.recipe-row-title,.recipe-row-ingredients';
    function translate(text) {
        if (language === 'en') return text;
        const trimmed = text.trim();
        if (dictionary[trimmed]) return text.replace(trimmed, dictionary[trimmed]);
        return text.replace(/Step (\d+) of (\d+)/g, 'Langkah $1 daripada $2')
            .replace(/Timer for step (\d+)/g, 'Pemasa untuk langkah $1')
            .replace(/Time is up for step (\d+):/g, 'Masa tamat untuk langkah $1:')
            .replace(/Seven days ending /g, 'Tujuh hari sehingga ')
            .replace(/Requested daily intake /g, 'Sasaran pengambilan harian ')
            .replace(/Current weight /g, 'Berat semasa ').replace(/Target weight /g, 'Berat sasaran ')
            .replace(/\bDay (\d+)/g, 'Hari $1').replace(/\bCarbs\b/g, 'Karbohidrat').replace(/\bFat\b/g, 'Lemak')
            .replace(/Use at most (\d+) characters\./g, 'Gunakan maksimum $1 aksara.')
            .replace(/Enter a number above 0 up to (\d+)\./g, 'Masukkan nombor melebihi 0 hingga $1.')
            .replace(/Enter a number from 0 up to (\d+)\./g, 'Masukkan nombor dari 0 hingga $1.')
            .replace(/Stop the active timer\?/g, 'Hentikan pemasa yang sedang berjalan?')
            .replace(/Delete /g, 'Padam ').replace(/Open /g, 'Buka ').replace(/Swap day /g, 'Tukar hari ')
            .replace(/breakfast/g, 'sarapan').replace(/lunch/g, 'makan tengah hari').replace(/dinner/g, 'makan malam').replace(/snack/g, 'snek')
            .replace(/This cannot be undone\./g, 'Tindakan ini tidak boleh dibatalkan.');
    }
    window.uiText = text => translate(text);
    function refresh() {
        observer.disconnect();
        document.documentElement.lang = language;
        selector.value = language;
        for (const radio of document.querySelectorAll('[name="ui-language"]')) {
            radio.checked = radio.value === language;
        }
        document.cookie = `language=${language};path=/;max-age=31536000;SameSite=Lax`;
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            if (node.parentElement.closest(protectedSelector)) continue;
            const previous = originals.get(node);
            const original = previous && node.textContent === previous.translated ? previous.original : node.textContent;
            const translated = translate(original);
            if (node.textContent !== translated) node.textContent = translated;
            originals.set(node, {original, translated});
        }
        for (const element of document.querySelectorAll('[placeholder],[aria-label],[data-confirm],title')) {
            if (element.closest('[data-user-content]')) continue;
            if (element.tagName === 'TITLE') {
                const title = element.textContent;
                element.textContent = language === 'ms' ? title.replace('Food tracker','Rekod makanan').replace('Meal planner','Perancang makanan').replace('recipes from your ingredients','resipi daripada bahan anda') : title.replace('Rekod makanan','Food tracker').replace('Perancang makanan','Meal planner').replace('resipi daripada bahan anda','recipes from your ingredients');
                continue;
            }
            const saved = attributes.get(element) || {};
            for (const name of ['placeholder','aria-label','data-confirm']) {
                if (!element.hasAttribute(name)) continue;
                const value = element.getAttribute(name);
                const old = saved[name];
                const original = old && value === old.translated ? old.original : value;
                const translated = translate(original);
                element.setAttribute(name,translated);
                saved[name]={original,translated};
            }
            attributes.set(element,saved);
        }
        observer.observe(document.body, {subtree:true, childList:true, characterData:true, attributes:true, attributeFilter:['aria-label','data-confirm','placeholder']});
    }
    const observer = new MutationObserver(refresh);
    selector.onchange = () => {
        language = selector.value === 'ms' ? 'ms' : 'en';
        try { localStorage.setItem('language',language); } catch {}
        document.cookie = `language=${language};path=/;max-age=31536000;SameSite=Lax`;
        refresh();
    };
    const segments = document.getElementById('languageOptions');
    if (segments) {
        selector.hidden = true;
        segments.hidden = false;
        document.querySelector('.language-label').setAttribute('for', '');
        for (const radio of document.querySelectorAll('[name="ui-language"]')) {
            radio.addEventListener('change', () => {
                selector.value = radio.value;
                selector.onchange();
            });
        }
    }
    refresh();
});
