/* Sauvegarde volontaire versionnée ; aucune communication réseau dans ce module. */
((root) => {
  'use strict';
  const CARNET = 'origin_vivant_local_v1', TREE = 'origin_arbre_vivant_v1';
  function carnet(value) {
    if (!value || typeof value !== 'object' || !value.draft || !Array.isArray(value.mirrors) || !Array.isArray(value.memories) || !Array.isArray(value.checkins)) throw Error('Carnet incompatible.');
    return value;
  }
  function tree(value) {
    if (!value || !Array.isArray(value.people) || value.people.length > 70) throw Error('Arbre incompatible.');
    return value;
  }
  function snapshot(storage) {
    const personal = carnet(JSON.parse(storage.getItem(CARNET) || 'null'));
    const family = JSON.parse(storage.getItem(TREE) || 'null');
    return {format:'origin-vivant-cloud-2', carnet:personal, tree:family && family.demo === false ? tree(family) : null};
  }
  function restore(payload, storage) {
    const values = new Map();
    if (payload?.format === 'origin-vivant-cloud-2') {
      values.set(CARNET, JSON.stringify(carnet(payload.carnet)));
      if (payload.tree !== null) values.set(TREE, JSON.stringify(tree(payload.tree)));
    } else {
      // Compatibilité avec les sauvegardes V2 initiales ne contenant que le carnet.
      if (payload?.format) throw Error('Version de sauvegarde non prise en charge.');
      values.set(CARNET, JSON.stringify(carnet(payload)));
    }
    const previous = new Map([...values.keys()].map(key => [key, storage.getItem(key)]));
    try { for (const [key,value] of values) storage.setItem(key,value); }
    catch(error) {
      for (const [key,value] of previous) {
        if (value === null) storage.removeItem(key); else storage.setItem(key,value);
      }
      throw error;
    }
  }
  const api = {snapshot, restore};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.OriginStorage = api;
})(globalThis);
