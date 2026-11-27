document.addEventListener('DOMContentLoaded', () => {
    const $ = id => document.getElementById(id);
    const sessions = new Map();
    let active;
    let interval;

    function render() {
        if (!active) return;
        $('stepTitle').textContent = `Step ${active.step + 1} of ${active.recipe.steps.length}`;
        $('instruction').textContent = active.recipe.steps[active.step];
        $('previous').disabled = active.step === 0;
        $('next').disabled = active.step === active.recipe.steps.length - 1;
        $('minutes').disabled = active.seconds > 0;
        $('timer').textContent = active.deadline ? 'Pause timer' : active.seconds ? 'Resume timer' : 'Start timer';
        $('stopTimer').hidden = !active.seconds;
        $('timerStep').textContent = active.seconds ? `Timer for step ${active.timerStep + 1}` : '';
        $('remaining').textContent = active.seconds ? `${Math.floor(active.seconds / 60)}:${String(active.seconds % 60).padStart(2, '0')}` : '';
    }

    function tick() {
        for (const state of sessions.values()) {
            if (!state.deadline) continue;
            state.seconds = Math.max(0, Math.ceil((state.deadline - Date.now()) / 1000));
            if (!state.seconds) {
                state.deadline = null;
                $('timerAnnouncement').textContent = `Time is up for step ${state.timerStep + 1}: ${state.recipe.steps[state.timerStep]}`;
            }
        }
        render();
        if (![...sessions.values()].some(state => state.deadline)) {
            clearInterval(interval);
            interval = null;
        }
    }

    document.addEventListener('cooking:start', event => {
        const recipe = event.detail;
        if (!recipe?.steps?.length) return;
        const key = recipe.id || recipe.recipe;
        if (!sessions.has(key)) sessions.set(key, {recipe, step:0, seconds:0, deadline:null});
        active = sessions.get(key);
        tick();
        $('cooking').showModal();
    });
    $('previous').onclick = () => { if (active.step > 0) active.step--; render(); };
    $('next').onclick = () => { if (active.step < active.recipe.steps.length - 1) active.step++; render(); };
    $('backToRecipe').onclick = () => $('cooking').close();
    $('timer').onclick = () => {
        if (active.deadline) {
            active.seconds = Math.max(0, Math.ceil((active.deadline - Date.now()) / 1000));
            active.deadline = null;
        } else {
            if (!$('minutes').reportValidity()) return;
            if (!active.seconds) {
                active.seconds = Number($('minutes').value) * 60;
                active.timerStep = active.step;
            }
            active.deadline = Date.now() + active.seconds * 1000;
            $('timerAnnouncement').textContent = '';
            if (!interval) interval = setInterval(tick, 250);
        }
        render();
    };
    $('stopTimer').onclick = () => {
        if (!confirm('Stop the active timer?')) return;
        active.deadline = null;
        active.seconds = 0;
        tick();
    };
    $('finish').onclick = () => {
        if (active.seconds && !confirm('Finish cooking and stop the active timer?')) return;
        active.deadline = null;
        active.seconds = 0;
        active.step = 0;
        tick();
        $('cooking').close();
    };
});
