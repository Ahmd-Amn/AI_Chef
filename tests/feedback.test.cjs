const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

for (const reducedMotion of [false, true]) {
    const handlers = {};
    const calls = [];
    const message = {
        textContent:'Submission failed',
        tabIndex:-1,
        hasAttribute:()=>false,
        setAttribute:(...args)=>calls.push(args),
        focus:options=>calls.push(['focus', options.preventScroll]),
        scrollIntoView:options=>calls.push(['scroll', options.behavior, options.block])
    };
    const window = {matchMedia:()=>({matches:reducedMotion}), addEventListener(){}};
    vm.runInNewContext(fs.readFileSync('public/static/feedback.js', 'utf8'), {
        window,
        document:{
            addEventListener:(name, handler)=>{handlers[name] = handler;},
            getElementById:()=>null,
            querySelector:()=>message,
            querySelectorAll:()=>[]
        }
    });
    handlers.DOMContentLoaded();
    assert.deepEqual(calls, [
        ['tabindex', '-1'], ['focus', true],
        ['scroll', reducedMotion ? 'instant' : 'smooth', 'center']
    ]);
    calls.length = 0;
    window.focusSubmissionError(null);
    assert.equal(calls.length, 0);
    window.focusSubmissionError(message);
    assert.equal(calls[1][0], 'focus');
    calls.length = 0;
    message.tabIndex = 0;
    window.focusSubmissionError(message);
    assert.equal(calls[0][0], 'focus');
    assert.equal(calls.length, 2);
}
console.log('Submission errors receive focus and scroll into view, respecting reduced motion.');

const handlers = {}, storage = new Map(), scrolls = [];
let popups = 0;
const popup = {hasAttribute:()=>true, showModal:()=>popups++};
const window = {
    scrollX:0, scrollY:600,
    scrollTo:options=>scrolls.push([options.left, options.top, options.behavior]),
    addEventListener:(name, handler)=>{handlers[name] = handler;}
};
vm.runInNewContext(fs.readFileSync('public/static/feedback.js', 'utf8'), {
    window, location:{pathname:'/tracker'},
    sessionStorage:{setItem:(key, value)=>storage.set(key, value), getItem:key=>storage.get(key), removeItem:key=>storage.delete(key)},
    document:{
        addEventListener:(name, handler)=>{handlers[name] = handler;},
        getElementById:id=>id === 'removedPopup' ? popup : null,
        querySelector:()=>null, querySelectorAll:()=>[]
    }
});
handlers.DOMContentLoaded();
handlers.submit({submitter:{value:'estimate'}});
assert.equal(storage.size, 0);
handlers.submit({submitter:{value:'delete_custom'}});
window.scrollY = 0;
handlers.load();
assert.equal(popups, 1);
assert.deepEqual(scrolls.at(-1), [0, 600, 'instant']);
assert.equal(storage.size, 0);
window.scrollY = 450;
window.showRemoved();
assert.equal(popups, 2);
assert.deepEqual(scrolls.at(-1), [0, 450, 'instant']);
console.log('Removal popups preserve position for page reloads and favorite removal.');
