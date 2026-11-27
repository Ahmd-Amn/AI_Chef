const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const handlers = {};
const input = {value:'',scrollTop:0,addEventListener(name, callback){handlers[name]=callback}};
const numbers = {};
const button = {disabled:false};
let submits = 0;
input.form = {requestSubmit(submitter){assert.equal(submitter,button); submits++;}};
vm.runInNewContext(fs.readFileSync('public/static/ingredients.js','utf8'), {
    document:{getElementById:id=>id==='ingredients'?input:id==='generateBtn'?button:numbers,addEventListener(name,callback){handlers[name]=callback}},
    window:{addEventListener(){}}
});
handlers.DOMContentLoaded();
assert.equal(numbers.textContent,'1.');
input.value='Chicken\nRice\n';
handlers.input();
assert.equal(numbers.textContent,'1.\n2.\n3.');
input.value='Rice';
handlers.input();
assert.equal(numbers.textContent,'1.');
input.scrollTop=28;
handlers.scroll();
assert.equal(numbers.scrollTop,28);
console.log('Ingredient numbering handles Enter, deletion and scrolling.');

let prevented = false;
handlers.keydown({key:'Enter',shiftKey:false});
assert.equal(submits,0);
handlers.keydown({key:'Enter',shiftKey:true,preventDefault(){prevented=true}});
assert.equal(submits,1);
assert.equal(prevented,true);
button.disabled=true;
handlers.keydown({key:'Enter',shiftKey:true,preventDefault(){}});
assert.equal(submits,1);
button.disabled=false;
handlers.keydown({key:'Enter',shiftKey:true,isComposing:true});
assert.equal(submits,1);
console.log('Shift+Enter submits once, preserves Enter and respects pending generation and composition.');
