/* Contrat de passage local. Aucun appel au moteur commercial ni collecte automatique. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const KEY = 'origin_premium_handoff_v1';
  const read = key => { try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch { return null; } };
  const status = text => { $('premiumStatus').textContent = text; };
  let people = [];

  function refresh() {
    const source = $('premiumSource').value;
    const tree = read('origin_arbre_vivant_v1');
    const mirror = read('origin_vivant_local_v1')?.draft;
    people = source === 'tree'
      ? (tree?.demo === false && Array.isArray(tree.people) ? tree.people : [])
      : (mirror && !mirror.demo ? [{id:'a',name:mirror.nameA,birth:mirror.birthA},{id:'b',name:mirror.nameB,birth:mirror.birthB}] : []);
    people = people.filter(p => p && typeof p.id === 'string' && typeof p.name === 'string' && p.name.trim()).slice(0,70);
    for (const id of ['premiumPersonA','premiumPersonB']) {
      $(id).replaceChildren(...people.map(person => {
        const option = document.createElement('option'); option.value = person.id; option.textContent = person.name.slice(0,60); return option;
      }));
    }
    if (people.length > 1) $('premiumPersonB').selectedIndex = 1;
    $('premiumSecond').hidden = $('premiumOffer').value !== 'couple';
    status(people.length ? 'Seuls les prénoms et dates sélectionnés seront repris. Aucun souvenir ni ressenti ne sera transféré.' : 'Crée un Miroir ou un arbre personnel pour préparer ton livret. Les personnages de démonstration restent séparés.');
    const localDemo = document.querySelector('meta[name="origin-demo-premium"]');
    $('premiumDemo').hidden = !localDemo;
  }

  function prepare() {
    if (!$('premiumConsent').checked) throw Error('Confirme ton choix de reprendre ces informations et l’autorisation des personnes concernées.');
    const ids = [$('premiumPersonA').value];
    if ($('premiumOffer').value === 'couple') ids.push($('premiumPersonB').value);
    if (ids.some(id => !id) || new Set(ids).size !== ids.length) throw Error('Choisis une personne pour Solo, ou deux personnes distinctes pour Couple.');
    const profiles = ids.map(id => people.find(p => p.id === id));
    if (profiles.some(p => !p)) throw Error('Profil indisponible ; actualise la sélection.');
    return {
      schema: 'origin.booklet-draft', version: 1, created_at: new Date().toISOString(),
      source: $('premiumSource').value, offre: $('premiumOffer').value, consent: true,
      clients: profiles.map(p => ({prenom: p.name.trim().slice(0,60), date_naissance: typeof p.birth === 'string' ? p.birth.slice(0,10) : ''}))
    };
  }

  $('premiumRefresh').addEventListener('click', refresh);
  $('premiumSource').addEventListener('change', refresh);
  $('premiumOffer').addEventListener('change', refresh);
  $('premiumExport').addEventListener('click', () => {
    try {
      const draft = prepare();
      const url = URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}));
      const link = document.createElement('a'); link.href=url; link.download='ORIGIN_dossier_livret.json'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status('Dossier enregistré sur cet appareil. Aucun envoi ni paiement effectué.');
    } catch(error) { status(error.message); }
  });
  $('premiumDemo').addEventListener('click', () => {
    try {
      const target = new URL(document.querySelector('meta[name="origin-demo-premium"]').content, location.origin);
      if (target.origin !== location.origin || target.pathname !== '/premium-demo/') throw Error('Destination de démonstration invalide.');
      sessionStorage.setItem(KEY, JSON.stringify(prepare()));
      location.assign(target.pathname + '?origin_handoff=1');
    } catch(error) { status(error.message); }
  });
  document.querySelectorAll('[data-go="premium"]').forEach(button => button.addEventListener('click', refresh));
  refresh();
})();
