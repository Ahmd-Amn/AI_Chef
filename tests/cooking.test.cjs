const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
const handlers = {};
let now = 1000;
let tick;
let allow = true;
function element(id) {
    if (!elements.has(id)) elements.set(id, {
        textContent:'', value:'1', reportValidity:()=>true,
        showModal(){this.open=true}, close(){this.open=false}
    });
    return elements.get(id);
}
vm.runInNewContext(fs.readFileSync('public/static/cooking.js', 'utf8'), {
    document:{getElementById:element, addEventListener(name, callback){handlers[name]=callback}},
    Date:{now:()=>now}, confirm:()=>allow,
    setInterval(callback){tick=callback;return 1}, clearInterval(){}
});
handlers.DOMContentLoaded();
const recipe = {id:1, steps:['Simmer', 'Serve']};
handlers['cooking:start']({detail:recipe});
element('timer').onclick();
element('next').onclick();
assert.equal(element('stepTitle').textContent, 'Step 2 of 2');
assert.equal(element('timer').textContent, 'Pause timer');
element('backToRecipe').onclick();
handlers['cooking:start']({detail:recipe});
assert.equal(element('stepTitle').textContent, 'Step 2 of 2');
allow = false;
element('stopTimer').onclick();
assert.equal(element('timer').textContent, 'Pause timer');
now += 61000;
tick();
assert.match(element('timerAnnouncement').textContent, /Time is up for step 1: Simmer/);
assert.equal(element('timer').textContent, 'Start timer');
console.log('Cooking step retention, timer continuity, stop confirmation and completion announcement passed.');
