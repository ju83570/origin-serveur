/* Données inventées de l'aperçu. Aucun accès API, compte, paiement ou email. */
(() => {
  'use strict';
  const TREE='origin_web_preview_tree_v1', CARNET='origin_web_preview_carnet_v1';
  const at='2026-10-23T10:00:00.000Z';
  const tree={demo:false,selected:'camille',anchor:'camille',people:[
    {id:'francoise',name:'Françoise Démo',birth:'1958-03-14',parents:[],partners:['pierre'],siblings:[],order:0,place:'Ville imaginaire',legacy:'Exemple fictif : le plaisir de raconter.',story:'Dans cet exemple inventé, elle aime transmettre des recettes.'},
    {id:'pierre',name:'Pierre Démo',birth:'1956-09-06',parents:[],partners:['francoise'],siblings:[],order:1,place:'Ville imaginaire',legacy:'Exemple fictif : la patience.',story:'Personnage inventé pour explorer les liens familiaux.'},
    {id:'camille',name:'Camille Démo',birth:'1988-04-12',parents:['francoise','pierre'],partners:['alex'],siblings:['lou'],order:10,place:'Ville imaginaire',legacy:'Exemple fictif : la curiosité.',story:'Un souvenir inventé : une promenade partagée.'},
    {id:'alex',name:'Alex Démo',birth:'1986-09-27',parents:[],partners:['camille'],siblings:[],order:11,place:'Ville imaginaire',legacy:'Exemple fictif : l’écoute.',story:'Ce profil est entièrement fictif.'},
    {id:'lou',name:'Lou Démo',birth:'1992-02-08',parents:['francoise','pierre'],partners:[],siblings:['camille'],order:12,place:'Ville imaginaire',legacy:'Exemple fictif : l’enthousiasme.',story:'Personnage inventé pour tester une relation de fratrie.'},
  ]};
  const carnet={
    draft:{relationship:'couple',nameA:'Camille Démo',nameB:'Alex Démo',birthA:'1988-04-12',birthB:'1986-09-27',profileAId:'camille',profileBId:'alex',issue:'incompris',feelingA:'tristesse',scene:'Exemple fictif : trouver un moment pour discuter.',needA:'ecoute',messageA:'Exemple inventé : j’aimerais prendre le temps de parler.',participatingB:false,demo:false},
    pages:[{id:'bienvenue-demo',subject:'libre',text:'Bienvenue dans ton Carnet d’Évolution. Cette page est un exemple fictif. Tu peux la modifier, la supprimer ou écrire ta propre page avec des informations inventées.',at,updatedAt:at}],
    mirrors:[],memories:[],checkins:[],journeyStart:'',ritualDone:[],
    constellation:{mode:'tree',a:'camille',b:'alex',relation:'auto',nameA:'',nameB:'',birthA:'',birthB:''},
  };
  let blocked=false;
  try {
    if(localStorage.getItem(TREE)===null)localStorage.setItem(TREE,JSON.stringify(tree));
    if(localStorage.getItem(CARNET)===null)localStorage.setItem(CARNET,JSON.stringify(carnet));
  }catch{blocked=true}
  document.addEventListener('DOMContentLoaded',()=>{
    if(blocked){const text=document.querySelector('.preview-banner span');if(text)text.textContent='Ton navigateur bloque le stockage : les modifications ne pourront pas être conservées.'}
    document.getElementById('previewReset')?.addEventListener('click',()=>{
      if(!confirm('Recommencer effacera uniquement les essais de cette démonstration sur cet appareil. Continuer ?'))return;
      try{
        for(const key of Object.keys(localStorage))if(key.startsWith('origin_web_preview_'))localStorage.removeItem(key);
        sessionStorage.removeItem('origin_web_preview_handoff_v1');
        history.replaceState(null,'',new URL('./#accueil',location.href));location.reload();
      }catch{alert('Le navigateur ne permet pas de réinitialiser le stockage de démonstration.')}
    });
  });
})();
