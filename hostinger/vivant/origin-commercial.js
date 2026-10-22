/* ORIGIN VIVANT — module commercial préparatoire, aucun paiement possible sans activation côté serveur. */
(()=>{'use strict';
const BASE='api/?op=';let csrf='',me=null,ent=null,apiReady=false,plans={},stripeTest=false;
const $=s=>document.querySelector(s);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const panel=document.createElement('section');panel.id='originAccount';panel.className='account-panel';panel.innerHTML=`<div class="account-content"><div><small class="account-eyebrow">✧ TON ESPACE ORIGIN VIVANT</small><h2>Un endroit à toi,<br><em>pour faire grandir les liens.</em></h2><p>Conserve tes réflexions et retrouve ton carnet. Ta sauvegarde en ligne reste un choix explicite, jamais automatique.</p></div><div class="account-actions" id="accountActions"><span class="account-status">Vérification du service…</span></div></div>`;
const footer=$('.footer');footer?.parentNode.insertBefore(panel,footer);
const modal=document.createElement('dialog');modal.className='account-dialog';modal.id='accountDialog';modal.innerHTML=`<div class="account-box"><button class="account-x" id="accountClose" aria-label="Fermer">×</button><span class="account-eyebrow">ESPACE PERSONNEL • ORIGIN</span><h2 id="accountTitle">Se connecter</h2><p id="accountDescription">Accède à ton espace sécurisé.</p><form id="accountForm"><label id="accountEmailLine">Email<input id="accountEmail" type="email" autocomplete="email" maxlength="190" required></label><label id="accountPasswordLine">Mot de passe<input id="accountPassword" type="password" autocomplete="current-password" minlength="12" required></label><label id="consentLine" class="account-consent" hidden><input id="accountConsent" type="checkbox"> J’accepte la <a href="confidentialite.html" target="_blank" rel="noopener">politique de confidentialité</a></label><button class="account-primary" id="accountSubmit">Continuer</button></form><p id="accountError" role="status"></p><button class="account-text" id="accountModeSwitch">Créer un compte</button><button class="account-text" id="accountForgot">Mot de passe oublié ?</button></div>`;document.body.append(modal);
const actions=$('#accountActions'),error=$('#accountError');let authMode='login';
const revisionKey=()=>`origin_cloud_revision_${me.id}`;
const setRevision=n=>sessionStorage.setItem(revisionKey(),String(n));
function download(state,label='SAUVEGARDE'){const url=URL.createObjectURL(new Blob([JSON.stringify(state,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`ORIGIN_${label}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}

const button=(label,action,kind='')=>`<button type="button" class="account-btn ${kind}" data-account="${action}">${label}</button>`;
function render(){if(!apiReady){actions.innerHTML='<span class="account-status">Espace sécurisé non encore installé sur cet hébergement.</span>';return;}
 if(me){const subscribed=!!ent?.plans?.length;actions.innerHTML=`<span class="account-status">✓ ${escape(me.email)}</span>`+button('☁ Sauvegarder mon carnet','save','gold')+button('↓ Récupérer ma sauvegarde','load')+button('Exporter ma sauvegarde en ligne','export')+button('Versions précédentes','versions')+(subscribed?button('Gérer mon abonnement','portal'):'')+(!subscribed && plans?.individual?.enabled?button(stripeTest?'Tester ORIGIN Personnel • aucun débit réel':'Activer ORIGIN Personnel • 9,90 €/mois','checkout_individual','gold'):'')+button('Déconnexion','logout')+button('Supprimer mon compte','delete');
 }else{actions.innerHTML=button('Se connecter','login','gold')+button('Créer mon compte','register')+'<small>Gratuit pendant la phase de vérification. Aucune vente n’est activée.</small>';
 }}
async function call(op,data=null){const init={credentials:'same-origin',headers:{'Accept':'application/json'}};if(data!==null){init.method='POST';init.headers['Content-Type']='application/json';init.headers['X-CSRF-Token']=csrf;init.body=JSON.stringify(data);}const r=await fetch(BASE+encodeURIComponent(op),init);let v;try{v=await r.json()}catch{throw new Error('Le serveur ne renvoie pas de réponse valide.');}if(!r.ok){const err=new Error(v.error||'Action impossible');err.code=v.code;throw err;}if(v.csrf)csrf=v.csrf;return v;}
async function refresh(){try{const r=await call('status');apiReady=true;csrf=r.csrf;me=r.user;ent=r.entitlements;plans=r.plans;stripeTest=r.stripe_test_mode===true;render();}catch{apiReady=false;render();}}
function deletionPassword(){return new Promise(resolve=>{const d=document.createElement('dialog');d.className='account-dialog';d.innerHTML='<form method=dialog class=account-box><h2>Confirmer la suppression</h2><label>Mot de passe actuel<input type=password autocomplete=current-password required></label><button value=delete>Supprimer définitivement</button><button type=button data-cancel>Annuler</button></form>';document.body.append(d);d.querySelector('[data-cancel]').onclick=()=>d.close('cancel');d.addEventListener('close',()=>{const value=d.returnValue==='delete'?d.querySelector('input').value:null;d.remove();resolve(value);},{once:true});d.showModal();});}
const resetToken=new URLSearchParams(location.search).get('reinitialiser');
function open(mode){
 authMode=mode;error.textContent='';
 const labels={login:'Se connecter',register:'Créer mon espace privé',forgot:'Retrouver mon accès',reset:'Choisir un nouveau mot de passe'};
 $('#accountTitle').textContent=labels[mode]||labels.login;
 $('#accountDescription').textContent=mode==='register'?'Confirme ton adresse email pour sécuriser ton compte.':mode==='forgot'?'Nous t’enverrons un lien valable 45 minutes si cette adresse possède un compte.':mode==='reset'?'Saisis un nouveau mot de passe de 12 caractères minimum.':'Retrouve tes souvenirs et ton parcours.';
 $('#consentLine').hidden=mode!=='register';
 $('#accountEmailLine').hidden=mode==='reset';$('#accountPasswordLine').hidden=mode==='forgot';
 $('#accountEmail').required=mode!=='reset';$('#accountPassword').required=mode!=='forgot';
 $('#accountPassword').autocomplete=(mode==='register'||mode==='reset')?'new-password':'current-password';
 $('#accountModeSwitch').textContent='Retour à la connexion';if(mode==='login')$('#accountModeSwitch').textContent='Créer un compte';
 $('#accountForgot').hidden=mode!=='login';
 $('#accountSubmit').textContent=mode==='register'?'Créer mon compte':mode==='forgot'?'Envoyer le lien':mode==='reset'?'Modifier mon mot de passe':'Connexion';
 if(!modal.open)modal.showModal();
}
modal.addEventListener('click',e=>{if(e.target===modal)modal.close();});$('#accountClose').addEventListener('click',()=>modal.close());$('#accountModeSwitch').addEventListener('click',()=>open(authMode==='login'?'register':'login'));$('#accountForgot').addEventListener('click',()=>open('forgot'));
$('#accountForm').addEventListener('submit',async e=>{e.preventDefault();error.textContent='';const b=$('#accountSubmit');b.disabled=true;try{const op=authMode==='forgot'?'password_reset_request':authMode==='reset'?'password_reset':authMode;
 const v=await call(op,{email:$('#accountEmail').value,password:$('#accountPassword').value,token:resetToken,consent:$('#accountConsent').checked});
 if(['register','forgot','reset'].includes(authMode)){
   error.textContent=v.message||'Opération effectuée.';
   if(authMode==='reset')history.replaceState({},'',location.pathname);
 }else{modal.close();me=v.user;ent=v.entitlements;render();}}catch(err){error.textContent=err.message;}finally{b.disabled=false;}});
actions.addEventListener('click',async e=>{const b=e.target.closest('[data-account]');if(!b)return;const action=b.dataset.account;if(action==='login'||action==='register'){open(action);return;}b.disabled=true;try{
 if(action==='logout'){sessionStorage.removeItem(revisionKey());await call('logout',{});me=null;ent=null;render();}
 if(action==='checkout_individual'){if(!confirm(stripeTest?'Ouvrir Stripe en mode test ? Aucun débit réel.':'Souscrire à ORIGIN Personnel à 9,90 € par mois ? Abonnement renouvelé automatiquement, résiliable depuis le portail de facturation.'))return;const result=await call('checkout',{plan:'individual'});if(result.checkout_url)location.assign(result.checkout_url);else throw Error('Page de paiement indisponible');}
 if(action==='save'){
   const owner=localStorage.getItem('origin_local_owner_v1');
   if(owner && owner!==String(me.id))throw Error('Ces données locales sont associées à un autre compte. Exporte-les puis utilise une fenêtre privée pour ton espace.');
   if(!confirm('Sauvegarder ton carnet et ton arbre personnel sur ce compte ? Vérifie que tu souhaites y associer les données de cet appareil.'))return;
   let revision=sessionStorage.getItem(revisionKey());
   if(revision===null){const remote=await call('load',{});if(remote.state)throw Error('Une sauvegarde existe déjà. Exporte ta copie locale puis récupère cette sauvegarde avant de la remplacer.');revision='0';}
   const state=OriginStorage.snapshot(localStorage);
   const result=await call('save',{state,base_revision:Number(revision)});
   setRevision(result.revision);localStorage.setItem('origin_local_owner_v1',String(me.id));alert(result.message);
 }
 if(action==='load' || action==='versions'){
   let revision=null;
   if(action==='versions'){
     const list=await call('versions',{});if(!list.versions.length)throw Error('Aucune version précédente.');
     const selected=prompt('Version à récupérer : '+list.versions.map(v=>`${v.revision} (${v.updated_at})`).join(', '));
     if(selected===null)return;revision=Number(selected);
     if(!Number.isSafeInteger(revision)||!list.versions.some(v=>Number(v.revision)===revision))throw Error('Choisis une version de la liste.');
   }
   const result=await call('load',revision===null?{}:{revision});
   if(!result.state)throw Error('Aucune sauvegarde en ligne trouvée.');
   if(!confirm('Cette récupération remplacera le carnet et l’arbre de cet appareil. Exporte d’abord ta copie locale pour la conserver. Continuer ?'))return;
   OriginStorage.restore(result.state,localStorage);setRevision(result.current_revision);
   localStorage.setItem('origin_local_owner_v1',String(me.id));location.reload();
 }
 if(action==='export'){const result=await call('export',{});if(!result.state)throw Error('Aucune sauvegarde en ligne trouvée.');download(result.state);}
 if(action==='delete'){
   if(!confirm('Supprimer définitivement ton compte, tes sauvegardes et leur historique ? Exporte tes données avant de continuer.'))return;
   const password=await deletionPassword();if(password===null)return;
   const result=await call('delete',{confirm:'SUPPRIMER',password});sessionStorage.removeItem(revisionKey());me=null;ent=null;render();alert(result.message);
 }
 if(action==='portal'){const result=await call('portal',{});if(!result.portal_url)throw Error('Portail de facturation indisponible');location.assign(result.portal_url);}
 }catch(err){alert(err.message);}finally{b.disabled=false;}});
refresh();if(resetToken && /^[a-f0-9]{64}$/.test(resetToken))open('reset');
})();
