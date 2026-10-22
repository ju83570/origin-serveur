/* ORIGIN VIVANT — module commercial préparatoire, aucun paiement possible sans activation côté serveur. */
(()=>{'use strict';
const BASE='api/?op=';let csrf='',me=null,ent=null,apiReady=false,plans={},stripeTest=false;
const $=s=>document.querySelector(s);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const panel=document.createElement('section');panel.id='originAccount';panel.className='account-panel';panel.innerHTML=`<div class="account-content"><div><small class="account-eyebrow">✧ TON ESPACE ORIGIN VIVANT</small><h2>Un endroit à toi,<br><em>pour faire grandir les liens.</em></h2><p>Conserve tes réflexions et retrouve ton carnet. Ta sauvegarde en ligne reste un choix explicite, jamais automatique.</p></div><div class="account-actions" id="accountActions"><span class="account-status">Vérification du service…</span></div></div>`;
const footer=$('.footer');footer?.parentNode.insertBefore(panel,footer);
const modal=document.createElement('dialog');modal.className='account-dialog';modal.id='accountDialog';modal.innerHTML=`<div class="account-box"><button class="account-x" id="accountClose" aria-label="Fermer">×</button><span class="account-eyebrow">ESPACE PERSONNEL • ORIGIN</span><h2 id="accountTitle">Se connecter</h2><p id="accountDescription">Accède à ton espace sécurisé.</p><form id="accountForm"><label id="accountEmailLine">Email<input id="accountEmail" type="email" autocomplete="email" maxlength="190" required></label><label id="accountPasswordLine">Mot de passe<input id="accountPassword" type="password" autocomplete="current-password" minlength="12" required></label><label id="consentLine" class="account-consent" hidden><input id="accountConsent" type="checkbox"> J’accepte la <a href="confidentialite.html" target="_blank" rel="noopener">politique de confidentialité</a></label><button class="account-primary" id="accountSubmit">Continuer</button></form><p id="accountError" role="status"></p><button class="account-text" id="accountModeSwitch">Créer un compte</button><button class="account-text" id="accountForgot">Mot de passe oublié ?</button></div>`;document.body.append(modal);
const actions=$('#accountActions'),error=$('#accountError');let authMode='login';
const button=(label,action,kind='')=>`<button type="button" class="account-btn ${kind}" data-account="${action}">${label}</button>`;
function render(){if(!apiReady){actions.innerHTML='<span class="account-status">Espace sécurisé non encore installé sur cet hébergement.</span>';return;}
 if(me){const subscribed=!!ent?.plans?.length;actions.innerHTML=`<span class="account-status">✓ ${escape(me.email)}</span>`+button('☁ Sauvegarder mon carnet','save','gold')+button('↓ Récupérer ma sauvegarde','load')+(subscribed?button('Gérer mon abonnement','portal'):'')+(!subscribed && plans?.individual?.enabled?button(stripeTest?'Tester ORIGIN Personnel • aucun débit réel':'Activer ORIGIN Personnel • 9,90 €/mois','checkout_individual','gold'):'')+button('Déconnexion','logout');
 }else{actions.innerHTML=button('Se connecter','login','gold')+button('Créer mon compte','register')+'<small>Gratuit pendant la phase de vérification. Aucune vente n’est activée.</small>';
 }}
async function call(op,data=null){const init={credentials:'same-origin',headers:{'Accept':'application/json'}};if(data!==null){init.method='POST';init.headers['Content-Type']='application/json';init.headers['X-CSRF-Token']=csrf;init.body=JSON.stringify(data);}const r=await fetch(BASE+encodeURIComponent(op),init);let v;try{v=await r.json()}catch{throw new Error('Le serveur ne renvoie pas de réponse valide.');}if(!r.ok)throw new Error(v.error||'Action impossible');if(v.csrf)csrf=v.csrf;return v;}
async function refresh(){try{const r=await call('status');apiReady=true;csrf=r.csrf;me=r.user;ent=r.entitlements;plans=r.plans;stripeTest=r.stripe_test_mode===true;render();}catch{apiReady=false;render();}}
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
 if(action==='logout'){await call('logout',{});me=null;ent=null;render();}
 if(action==='checkout_individual'){if(!confirm(stripeTest?'Ouvrir Stripe en mode test ? Aucun débit réel.':'Souscrire à ORIGIN Personnel à 9,90 € par mois ? Abonnement renouvelé automatiquement, résiliable depuis le portail de facturation.'))return;const result=await call('checkout',{plan:'individual'});if(result.checkout_url)location.assign(result.checkout_url);else throw Error('Page de paiement indisponible');}
 if(action==='save'){if(!confirm('Sauvegarder ton carnet et ton arbre personnel, s’il existe, sur le serveur ORIGIN ? Noms, dates, photos et notes seront chiffrés au repos pour ton compte. Rien n’est envoyé sans ce choix.'))return;const state=OriginStorage.snapshot(localStorage);const result=await call('save',{state});alert(result.message||'Sauvegarde effectuée');}
 if(action==='load'){const result=await call('load',{});if(!result.state)throw Error('Aucune sauvegarde en ligne trouvée.');if(!confirm('La sauvegarde en ligne va remplacer ton carnet et l’arbre qu’elle contient sur cet appareil. Avant de continuer, tu peux exporter tes données depuis Mon Carnet. Continuer ?'))return;OriginStorage.restore(result.state,localStorage);location.reload();}
 if(action==='portal'){const result=await call('portal',{});if(!result.portal_url)throw Error('Portail de facturation indisponible');location.assign(result.portal_url);}
 }catch(err){alert(err.message);}finally{b.disabled=false;}});
refresh();if(resetToken && /^[a-f0-9]{64}$/.test(resetToken))open('reset');
})();
