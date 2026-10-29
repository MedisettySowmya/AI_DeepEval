// Offline checks for form state. No browser, server, or model is launched.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0]
  .split("window.addEventListener('beforeunload'")[0];
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    value: '', disabled: false, textContent: '', innerHTML: '',
    classList: {toggle() {}, add() {}, remove() {}},
    addEventListener() {}, scrollIntoView() {},
    querySelector() {return element('notice');},
    insertAdjacentHTML() {},
  });
  return elements.get(id);
}
const context = vm.createContext({
  document: {
    getElementById: element,
    querySelectorAll: () => ['edit-question', 'edit-context', 'edit-truth',
      'edit-instructions', 'reset-case'].map(element),
  },
  window: {}, console, setTimeout, clearTimeout,
});
vm.runInContext(script, context);
vm.runInContext(`
  jobId='example';job={state:'awaiting_review',workbook:null};
  report={case:{input:'Question',context:'Source'},runs:[{
    run:1,test_case:{input:'Question',context:'Source'},
    suggestion:{recommendations:['Answer directly.']}
  }]};
  syncReviewEditor();
`, context);
// The form is unlocked and contains the proposed instructions for review.
assert.equal(element('edit-context').disabled, false);
assert.equal(element('reset-case').disabled, false);
assert.match(element('source').innerHTML, /edit-context/);
// Source inserts the instructions and approval controls into the same section.
let inserted = '';
element('source').insertAdjacentHTML = (_, content) => {inserted = content;};
vm.runInContext("source({input:'Question',context:'Source',instructions:'Answer directly.'},null,'manual')", context);
assert.match(inserted, /id="edit-instructions"/);
assert.match(inserted, /Answer directly\./);
assert.match(inserted, /Approve & re-run/);

// Polling must preserve the reviewer's in-progress changes.
element('edit-context').value = 'Unsaved human edit';
const previous = element('source').innerHTML;
vm.runInContext('syncReviewEditor()', context);
assert.equal(element('source').innerHTML, previous);
assert.equal(element('edit-context').value, 'Unsaved human edit');

// Analysis provides guidance, with no second textarea or approval button.
const analysis = vm.runInContext(`reviewPanel({run:1,suggestion:{
  causes:[],recommendations:['Answer directly.']
}})`, context);
assert.ok(analysis.includes('#source-panel'));
assert.ok(!analysis.includes('<textarea'));
assert.ok(!analysis.includes('id="approve"'));

vm.runInContext("job.state='generating';lockEditor()", context);
assert.equal(element('edit-context').disabled, true);
assert.equal(element('reset-case').disabled, true);
console.log('UI form review checks passed.');
