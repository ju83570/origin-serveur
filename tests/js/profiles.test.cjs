const {test} = require('node:test');
const assert = require('node:assert/strict');
const {read, normalize, pair, relation, validDate, route} = require('../../hostinger/vivant/origin-profiles.js');
const people = () => normalize([
  {id:'parent',name:'Claude Exemple',birth:'1960-03-12'},
  {id:'a',name:'Lina Exemple',birth:'1990-05-12',parents:['parent'],partners:['partner']},
  {id:'b',name:'Noé Exemple',birth:'1992-09-23',parents:['parent']},
  {id:'partner',name:'Alex Exemple',birth:'1988-09-23'},
  {id:'other',name:'Sam Exemple',birth:'1989-06-01'}
]);

test('seul un arbre personnel valide fournit des profils, sans écriture', () => {
  for (const raw of [null,JSON.stringify({demo:true,people:people()})]) assert.deepEqual(read({getItem:()=>raw}),[]);
  const source = JSON.stringify({demo:false,people:people(),selected:'a'});
  const result = read({getItem:()=>source,setItem:()=>assert.fail('aucune écriture attendue')});
  assert.equal(result[1].name,'Lina Exemple');
});
test('un arbre incompatible ne devient jamais silencieusement un arbre vide', () => {
  for (const raw of ['{',JSON.stringify({people:[]}),JSON.stringify({demo:false,people:'invalid'})]) assert.throws(()=>read({getItem:()=>raw}));
  assert.throws(()=>normalize([{id:'a',name:'Lina'},{id:'a',name:'Autre'}]));
  assert.throws(()=>normalize([{id:'__proto__',name:'Profil'}]));
});
test('les profils sont minimisés sans photo, souvenir ou données copiées', () => {
  const result=normalize([{id:'a',name:'Lina',story:'Ne pas copier',photo:'Ne pas copier',parents:['missing'],birth:'2021-02-29'}])[0];
  assert.equal(result.story,undefined);assert.equal(result.photo,undefined);assert.equal(result.birth,'');assert.deepEqual(result.parents,[]);
});
test('les dates historiques de l’Arbre et les années bissextiles sont cohérentes', () => {
  assert.equal(validDate('1850-01-01'),true);assert.equal(validDate('2000-02-29'),true);
  for (const date of ['1849-12-31','1900-02-29','2020-13-01','2020-01-32','invalid']) assert.equal(validDate(date),false);
});
test('parent enfant dans les deux sens, fratrie et partenariat documentés', () => {
  const p=people();
  assert.equal(relation(p,'parent','a').kind,'parent_child');assert.match(relation(p,'a','parent').label,/parent/);
  assert.equal(relation(p,'a','b').kind,'siblings');assert.equal(relation(p,'a','partner').kind,'partners');
  assert.equal(relation(p,'partner','a').documented,true);
});
test('fratrie déclarée sans parents et inconnus sans présomption de couple', () => {
  const p=normalize([{id:'a',name:'Lina',siblings:['b']},{id:'b',name:'Alex'},{id:'c',name:'Sam'}]);
  assert.equal(relation(p,'a','b').kind,'siblings');
  for (const [a,b] of [['a','c'],['a','a'],['absent','a']]) assert.deepEqual(relation(p,a,b),{kind:'other',label:'Autre lien',documented:false});
});
test('relations contradictoires ou parents inconnus ne créent pas de conclusion', () => {
  const p=normalize([{id:'a',name:'Lina',parents:['b'],partners:['b']},{id:'b',name:'Alex'}]);
  assert.equal(relation(p,'a','b').kind,'other');assert.equal(relation(p,'a','b').ambiguous,true);
  const unknown=normalize([{id:'a',name:'Lina',parents:['absent']},{id:'b',name:'Alex',parents:['absent']}]);
  assert.equal(relation(unknown,'a','b').kind,'other');
});
test('une nouvelle première personne conserve la seconde quand elle est distincte', () => {
  const current={a:'a',b:'b'};assert.deepEqual(pair(current,people(),'a','other'),{a:'other',b:'b'});assert.deepEqual(current,{a:'a',b:'b'});
});
test('une collision échange les profils ou vide la sélection sans doublon', () => {
  assert.deepEqual(pair({a:'a',b:'b'},people(),'a','b'),{a:'b',b:'a'});
  assert.deepEqual(pair({a:'',b:'b'},people(),'a','b'),{a:'b',b:''});
  assert.deepEqual(pair({a:'a',b:'a'},people()),{a:'a',b:''});
});
test('suppression et sélection périmée ne récupèrent pas arbitrairement un profil', () => {
  assert.deepEqual(pair({a:'deleted',b:'b'},people()),{a:'',b:'b'});
  assert.deepEqual(pair({a:'a',b:'b'},people(),'b','absent'),{a:'a',b:''});
});
test('le lien contient seulement un identifiant dans le fragment, sans données personnelles', () => {
  assert.deepEqual(route('#constellation/a%2Fb'),{view:'constellation',person:'a/b'});
  assert.deepEqual(route('#constellation/%ZZ'),{view:'constellation',person:''});
  assert.equal(route('#constellation/'+'a'.repeat(66)).person,'');
  assert.deepEqual(route('#constellation/demo'),{view:'constellation',person:'demo'});
});
