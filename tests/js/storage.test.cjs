const {test} = require('node:test');
const assert = require('node:assert/strict');
const {snapshot, restore, recover} = require('../../hostinger/vivant/origin-storage.js');
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

test('une restauration complète sans arbre supprime celui du compte précédent',()=>{
 const s=store({[C]:JSON.stringify(notebook()),[T]:JSON.stringify({demo:false,people:[{id:'ancien'}]})});
 restore({format:'origin-vivant-cloud-2',carnet:notebook(),tree:null},s);
 assert.equal(s.getItem(T),null);
});
test('un export ancien reste importable et conserve l’arbre local',()=>{
 const s=store({[T]:JSON.stringify({demo:false,people:[]})});
 restore({format:'origin-vivant-1',data:notebook()},s);
 assert.deepEqual(JSON.parse(s.getItem(C)),notebook());assert.notEqual(s.getItem(T),null);
});
test('impossibilité de créer le journal : aucune donnée remplacée',()=>{
 const s=store({[C]:'copie originale',[T]:'arbre original'});const before=[...s.values];
 s.setItem=()=>{throw Error('quota')};
 assert.throws(()=>restore({format:'origin-vivant-cloud-2',carnet:notebook(),tree:null},s),/quota/);
 assert.deepEqual([...s.values],before);
});
test('récupération après une interruption au milieu de la restauration',()=>{
 const s=store({[C]:'partiel',[T]:'nouvel arbre',origin_restore_recovery_v1:JSON.stringify([[C,'ancien carnet'],[T,null]])});
 recover(s);assert.equal(s.getItem(C),'ancien carnet');assert.equal(s.getItem(T),null);assert.equal(s.getItem('origin_restore_recovery_v1'),null);
});
test('une restauration refusée conserve un journal récupérable si le rollback échoue',()=>{
 const s=store({[C]:'ancien carnet',[T]:'ancien arbre'});const write=s.setItem;
 s.setItem=(k,v)=>{if(k===T || (k===C&&v==='ancien carnet'))throw Error('quota');write(k,v)};
 assert.throws(()=>restore({format:'origin-vivant-cloud-2',carnet:notebook(),tree:{demo:false,people:[]}},s));
 assert.notEqual(s.getItem('origin_restore_recovery_v1'),null);
 s.setItem=write;recover(s);assert.equal(s.getItem(C),'ancien carnet');assert.equal(s.getItem(T),'ancien arbre');
});
test('un arbre personnel corrompu est signalé plutôt qu’omis de la sauvegarde',()=>{
 const s=store({[C]:JSON.stringify(notebook()),[T]:JSON.stringify({demo:false,people:'corrompu'})});
 assert.throws(()=>snapshot(s));
});
