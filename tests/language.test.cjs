const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
(async () => {
    let loaded;
    const selector = {};
    const nodes = ['Meal planner','Estimate nutrition','Logging in…'].map(textContent=>({
        textContent,parentElement:{closest:()=>null}
    }));
    const document = {
        body:{}, documentElement:{},cookie:'',
        getElementById:id=>id==='language'?selector:null,
        addEventListener(name, callback){loaded=callback},
        querySelectorAll:()=>[],
        createTreeWalker(){let index=0;return {nextNode:()=>nodes[index++]}}
    };
    const storage = {language:'ms'};
    const context = {
        document,window:{},NodeFilter:{SHOW_TEXT:4},
        localStorage:{getItem:key=>storage[key],setItem(key,value){storage[key]=value}},
        fetch:async()=>({ok:true,json:async()=>JSON.parse(fs.readFileSync('public/static/ms.json','utf8'))}),
        MutationObserver:class {disconnect(){} observe(){}}
    };
    vm.runInNewContext(fs.readFileSync('public/static/language.js','utf8'),context);
    await loaded();
    assert.equal(document.documentElement.lang,'ms');
    assert.equal(nodes[0].textContent,'Perancang makanan');
    assert.equal(nodes[2].textContent,'Sedang log masuk…');
    selector.value='en';selector.onchange();
    assert.equal(nodes[0].textContent,'Meal planner');
    assert.equal(nodes[1].textContent,'Estimate nutrition');
    assert.equal(storage.language,'en');
    assert.match(document.cookie,/language=en/);
    selector.value='ms';selector.onchange();
    assert.equal(nodes[1].textContent,'Anggar nutrisi');
    console.log('Language persistence, Malay interface/loading text and reversible switching passed.');
})();
