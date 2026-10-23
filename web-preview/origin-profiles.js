/* Profils partagés : l'Arbre est la seule source des personnes et de leurs liens.
   Aucun âge, prénom ou nombre ne permet de déduire une relation. Aucun réseau. */
((root) => {
  'use strict';
  const KEY = 'origin_web_preview_tree_v1';
  function validDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return false;
    const [y,m,d] = value.split('-').map(Number), date = new Date(Date.UTC(y,m-1,d));
    return y >= 1850 && y <= 2100 && date.getUTCFullYear() === y && date.getUTCMonth() === m-1 && date.getUTCDate() === d;
  }
  function normalize(people) {
    if (!Array.isArray(people) || people.length > 70) throw Error('Arbre incompatible. Exporte une copie avant de le vérifier.');
    const ids = new Set();
    const result = people.map(p => {
      if (!p || typeof p.id !== 'string' || !p.id || p.id.length > 65 || ['__proto__','constructor','prototype'].includes(p.id) || ids.has(p.id)
          || typeof p.name !== 'string' || !p.name.trim() || p.name.length > 46) throw Error('Profils de l’Arbre incompatibles. Aucune donnée n’a été remplacée.');
      ids.add(p.id);
      return {id:p.id, name:p.name, birth:validDate(p.birth) ? p.birth : '',
        parents:Array.isArray(p.parents) ? p.parents.filter(x => typeof x === 'string') : [],
        partners:Array.isArray(p.partners) ? p.partners.filter(x => typeof x === 'string') : [],
        siblings:Array.isArray(p.siblings) ? p.siblings.filter(x => typeof x === 'string') : []};
    });
    for (const p of result) for (const key of ['parents','partners','siblings']) p[key] = [...new Set(p[key].filter(id => ids.has(id) && id !== p.id))];
    return result;
  }
  function read(storage) {
    const value = JSON.parse(storage.getItem(KEY) || 'null');
    if (!value || value.demo === true) return [];
    if (value.demo !== false) throw Error('Format de l’Arbre inconnu. Exporte-le avant de le vérifier.');
    return normalize(value.people);
  }
  function pair(current, people, side, id) {
    const ids = new Set(people.map(p => p.id));
    const next = {a:ids.has(current?.a) ? current.a : '', b:ids.has(current?.b) ? current.b : ''};
    if (side === 'a' || side === 'b') {
      const other = side === 'a' ? 'b' : 'a', old = next[side];
      next[side] = ids.has(id) ? id : '';
      if (next[side] && next[side] === next[other]) next[other] = old !== id && ids.has(old) ? old : '';
    }
    if (next.a === next.b) next.b = '';
    return next;
  }
  function relation(people, aId, bId) {
    const a = people.find(p => p.id === aId), b = people.find(p => p.id === bId);
    const other = {kind:'other', label:'Autre lien', documented:false};
    if (!a || !b || a === b) return other;
    const found = [];
    if (a.parents.includes(b.id)) found.push({kind:'parent_child',label:b.name+' est un parent de '+a.name});
    if (b.parents.includes(a.id)) found.push({kind:'parent_child',label:a.name+' est un parent de '+b.name});
    if (a.partners.includes(b.id) || b.partners.includes(a.id)) found.push({kind:'partners',label:'Partenaires renseignés dans l’Arbre'});
    if (a.siblings.includes(b.id) || b.siblings.includes(a.id) || a.parents.some(id => b.parents.includes(id))) found.push({kind:'siblings',label:'Fratrie renseignée dans l’Arbre'});
    return found.length === 1 ? {...found[0],documented:true} : found.length > 1 ? {...other,ambiguous:true} : other;
  }
  function fillSelect(select, people, selected, excluded = '') {
    const placeholder = document.createElement('option'); placeholder.value = ''; placeholder.textContent = 'Choisir une personne';
    select.replaceChildren(placeholder, ...people.map(p => {
      const option = document.createElement('option'); option.value = p.id;
      option.textContent = p.name + (p.birth ? ' · né(e) en '+p.birth.slice(0,4) : ' · date non renseignée');
      option.disabled = p.id === excluded; return option;
    }));
    select.value = people.some(p => p.id === selected && p.id !== excluded) ? selected : '';
  }
  function route(hash) {
    const [view, encoded = ''] = String(hash || '').replace(/^#/, '').split('/');
    let person = ''; try { person = decodeURIComponent(encoded); } catch { /* lien non valide : sélection inchangée */ }
    return {view,person:person.length <= 65 ? person : ''};
  }
  const api = {read, normalize, pair, relation, fillSelect, validDate, route};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.OriginProfiles = api;
})(globalThis);
