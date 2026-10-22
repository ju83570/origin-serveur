/* Sauvegarde volontaire versionnée ; aucune communication réseau dans ce module. */
((root) => {
  'use strict';
  const CARNET = 'origin_vivant_local_v1', TREE = 'origin_arbre_vivant_v1';
  const RECOVERY = 'origin_restore_recovery_v1';
  function carnet(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || !value.draft || typeof value.draft !== 'object' || Array.isArray(value.draft) || !Array.isArray(value.mirrors) || !Array.isArray(value.memories) || !Array.isArray(value.checkins) || [value.mirrors,value.memories,value.checkins].some(v => v.length > 300)) throw Error('Carnet incompatible.');
    return value;
  }
  function tree(value) {
    if (!value || value.demo !== false || !Array.isArray(value.people) || value.people.length > 70) throw Error('Arbre incompatible.');
    return value;
  }
  function snapshot(storage) {
    const personal = carnet(JSON.parse(storage.getItem(CARNET) || '{"draft":{},"mirrors":[],"memories":[],"checkins":[]}'));
    const family = JSON.parse(storage.getItem(TREE) || 'null');
    if (family && family.demo !== true) tree(family); // ne pas ignorer silencieusement un arbre corrompu
    return {format:'origin-vivant-cloud-2', carnet:personal, tree:family && family.demo === false ? tree(family) : null};
  }
  function recover(storage) {
    const journal=storage.getItem(RECOVERY);
    if (!journal) return;
    const previous=JSON.parse(journal);
    if (!Array.isArray(previous) || previous.some(v=>!Array.isArray(v)||![CARNET,TREE].includes(v[0])||(v[1]!==null&&typeof v[1]!=='string'))) throw Error('Copie de récupération incompatible.');
    for (const [key,value] of previous) { if(value===null) storage.removeItem(key); else storage.setItem(key,value); }
    storage.removeItem(RECOVERY);
  }
  function restore(payload, storage) {
    recover(storage);
    const values = new Map();
    if (payload?.format === 'origin-vivant-1') payload=payload.data;
    if (payload?.format === 'origin-vivant-cloud-2') {
      values.set(CARNET, JSON.stringify(carnet(payload.carnet)));
      if (!Object.hasOwn(payload,'tree')) throw Error('Arbre absent du format de sauvegarde.');
      values.set(TREE, payload.tree === null ? null : JSON.stringify(tree(payload.tree)));
    } else {
      // Compatibilité avec les sauvegardes V2 initiales ne contenant que le carnet.
      if (payload?.format) throw Error('Version de sauvegarde non prise en charge.');
      values.set(CARNET, JSON.stringify(carnet(payload)));
    }
    const previous = new Map([...values.keys()].map(key => [key, storage.getItem(key)]));
    // Journal durable AVANT toute écriture : si le quota empêche sa création,
    // aucune donnée existante n'est touchée. Un arrêt au milieu reste réparable.
    storage.setItem(RECOVERY,JSON.stringify([...previous]));
    try {
      for (const [key,value] of values) { if(value===null)storage.removeItem(key);else storage.setItem(key,value); }
      storage.removeItem(RECOVERY);
    }
    catch(error) {
      let failed=false;
      for (const [key,value] of previous) {
        try { if (value === null) storage.removeItem(key); else storage.setItem(key,value); }
        catch { failed=true; }
      }
      if(!failed)storage.removeItem(RECOVERY);
      throw error;
    }
  }
  const api = {snapshot, restore, recover, validateCarnet:carnet};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.OriginStorage = api;
})(globalThis);
