const {test} = require('node:test');
const assert = require('node:assert/strict');
const {snapshot, restore} = require('../../hostinger/vivant/origin-storage.js');
const C='origin_vivant_local_v1', T='origin_arbre_vivant_v1';
const notebook=()=>({draft:{nameA:'Lina'},mirrors:[],memories:[],checkins:[]});
function store(initial={}) {const values=new Map(Object.entries(initial));return {values,getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};}

test('carnet et arbre personnel inclus, sans données fictives par défaut',()=>{
 const s=store({[C]:JSON.stringify(notebook()),[T]:JSON.stringify({demo:false,people:[{id:'a',name:'Lina'}]})});
 assert.equal(snapshot(s).tree.people[0].name,'Lina');
 s.setItem(T,JSON.stringify({demo:true,people:[{id:'fiction'}]}));assert.equal(snapshot(s).tree,null);
});
test('restauration des deux espaces et compatibilité avec ancien carnet',()=>{
 const s=store();const tree={demo:false,people:[]};
 restore({format:'origin-vivant-cloud-2',carnet:notebook(),tree},s);
 assert.deepEqual(JSON.parse(s.getItem(T)),tree);
 restore(notebook(),s);assert.deepEqual(JSON.parse(s.getItem(T)),tree);
});
test('échec de stockage : restauration des valeurs précédentes',()=>{
 const s=store({[C]:JSON.stringify(notebook()),[T]:'{"people":[],"demo":false}'});
 const previous=[...s.values];const write=s.setItem;let failed=false;
 s.setItem=(key,value)=>{if(key===T&&!failed){failed=true;throw Error('quota')}return write(key,value)};
 assert.throws(()=>restore({format:'origin-vivant-cloud-2',carnet:{...notebook(),memories:[{text:'nouveau'}]},tree:{people:[],demo:false}},s),/quota/);
 assert.deepEqual([...s.values],previous);
});
test('format futur et contenu invalide ne remplacent aucune donnée',()=>{
 for(const bad of [{format:'future'},null,{format:'origin-vivant-cloud-2',carnet:notebook(),tree:{people:'invalid'}}]) {
  const s=store({[C]:'original'});assert.throws(()=>restore(bad,s));assert.equal(s.getItem(C),'original');
 }
});
