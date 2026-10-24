/*
 * ORIGIN : photos facultatives dans le formulaire du livret (merci.html)
 *
 * Installation : ajouter UNE ligne avant </body> dans merci.html, et rien d'autre :
 *   <script src="origin-photos.js" defer></script>
 *
 * Ce que ça fait :
 *  - ajoute, avant le bouton d'envoi, un bloc « Tes photos (facultatif) » avec une case par personne
 *    (les cases suivent les prénoms saisis) et une photo de groupe dès qu'il y a 2 personnes ou plus ;
 *  - réduit chaque photo dans le navigateur (900 px, JPEG) : rapide, même avec le réseau d'un téléphone ;
 *  - joint les photos à la requête d'envoi vers le serveur (champs photo1..photo10 et photo_groupe) ;
 *  - ne bloque JAMAIS l'envoi : sans photo, rien ne change ; si le serveur refuse la requête avec photos,
 *    elle est renvoyée automatiquement sans les photos.
 * Le serveur recadre, redresse et place les photos tout seul (couverture, portraits, photo de groupe).
 */
(function () {
  'use strict';
  var MAX_PX = 900, QUALITE = 0.82, MAX_TOTAL = 7 * 1024 * 1024; // ~7 Mo de texte base64 au maximum
  var photos = {};           // { photo1: dataURL, ..., photo_groupe: dataURL }
  var racine = null, form = null, sansPhotos = false;   // sansPhotos : après un échec réseau, on n'insiste pas avec les photos

  function qsa(s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); }
  function nbChamps() {
    var n = 0;
    for (var i = 1; i <= 10; i++) if (document.querySelector('[name="prenom' + i + '"]')) n = i;
    return n;
  }
  function prenom(i) {
    var el = document.querySelector('[name="prenom' + i + '"]');
    return (el && el.value && el.value.trim()) || (i === 1 ? 'Toi' : 'Personne ' + i);
  }

  // ── Réduction d'une photo ──────────────────────────────────────────────
  function reduire(fichier) {
    return new Promise(function (ok, ko) {
      function dessiner(src, w, h) {
        var k = Math.min(1, MAX_PX / Math.max(w, h));
        var c = document.createElement('canvas');
        c.width = Math.round(w * k); c.height = Math.round(h * k);
        var x = c.getContext('2d');
        x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
        x.drawImage(src, 0, 0, c.width, c.height);
        ok(c.toDataURL('image/jpeg', QUALITE));
      }
      if (window.createImageBitmap) {
        createImageBitmap(fichier, { imageOrientation: 'from-image' }).then(function (b) {
          dessiner(b, b.width, b.height);
        }).catch(function () { viaImg(); });
      } else { viaImg(); }
      function viaImg() {
        var url = URL.createObjectURL(fichier), im = new Image();
        im.onload = function () { dessiner(im, im.naturalWidth, im.naturalHeight); URL.revokeObjectURL(url); };
        im.onerror = function () { URL.revokeObjectURL(url); ko(new Error('image illisible')); };
        im.src = url;
      }
    });
  }

  function total() { return Object.keys(photos).reduce(function (s, k) { return s + photos[k].length; }, 0); }

  // ── Interface ──────────────────────────────────────────────────────────
  function css() {
    if (document.getElementById('origin-photos-css')) return;
    var s = document.createElement('style'); s.id = 'origin-photos-css';
    s.textContent =
      '#origin-photos{margin:1.6rem 0;padding:1.2rem 1.2rem 1rem;border:1px solid rgba(201,168,76,.35);border-radius:14px;background:rgba(201,168,76,.05)}' +
      '#origin-photos h3{margin:0 0 .3rem;font-size:1.05rem;letter-spacing:.04em}' +
      '#origin-photos .op-sub{margin:0 0 1rem;font-size:.9rem;opacity:.75;line-height:1.45}' +
      '#origin-photos .op-grille{display:flex;flex-wrap:wrap;gap:.9rem}' +
      '#origin-photos .op-case{position:relative;width:104px;text-align:center;font-size:.78rem}' +
      '#origin-photos .op-case.op-groupe{width:156px}' +
      '#origin-photos label{display:flex;align-items:center;justify-content:center;width:100%;aspect-ratio:1;border:1.5px dashed rgba(201,168,76,.6);border-radius:50%;cursor:pointer;overflow:hidden;background-size:cover;background-position:center;font-size:1.6rem;color:#C9A84C}' +
      '#origin-photos .op-groupe label{aspect-ratio:4/3;border-radius:12px}' +
      '#origin-photos .op-case.op-ok label{border-style:solid;color:transparent}' +
      '#origin-photos input[type=file]{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}' +
      '#origin-photos .op-nom{display:block;margin-top:.4rem;line-height:1.2;word-break:break-word}' +
      '#origin-photos .op-x{position:absolute;top:-6px;right:-6px;width:22px;height:22px;border-radius:50%;border:0;background:#222;color:#fff;font-size:13px;line-height:22px;padding:0;cursor:pointer;display:none}' +
      '#origin-photos .op-ok .op-x{display:block}' +
      '#origin-photos .op-msg{margin:.8rem 0 0;font-size:.8rem;color:#b5651d;min-height:1em}';
    document.head.appendChild(s);
  }

  function ajouterCase(grille, cle, nom, groupe) {
    var d = document.createElement('div');
    d.className = 'op-case' + (groupe ? ' op-groupe' : '') + (photos[cle] ? ' op-ok' : '');
    d.setAttribute('data-cle', cle);
    var id = 'op-' + cle;
    d.innerHTML = '<label for="' + id + '" title="Ajouter une photo">+</label>' +
      '<input type="file" id="' + id + '" accept="image/*" tabindex="-1">' +
      '<button type="button" class="op-x" aria-label="Retirer la photo">×</button>' +
      '<span class="op-nom"></span>';
    d.querySelector('.op-nom').textContent = nom;
    var lab = d.querySelector('label');
    if (photos[cle]) lab.style.backgroundImage = 'url(' + photos[cle] + ')';
    d.querySelector('input').addEventListener('change', function (e) {
      var f = e.target.files && e.target.files[0]; if (!f) return;
      var msg = racine.querySelector('.op-msg'); msg.textContent = '';
      reduire(f).then(function (u) {
        var avant = photos[cle] ? photos[cle].length : 0;
        if (total() - avant + u.length > MAX_TOTAL) { msg.textContent = 'Il y a déjà beaucoup de photos : ton livret sera livré normalement avec celles déjà ajoutées.'; return; }
        photos[cle] = u; lab.style.backgroundImage = 'url(' + u + ')'; d.classList.add('op-ok');
      }).catch(function () { msg.textContent = 'Cette photo n’a pas pu être lue. Pas de souci, tu peux continuer sans elle.'; });
      e.target.value = '';
    });
    d.querySelector('.op-x').addEventListener('click', function () {
      delete photos[cle]; lab.style.backgroundImage = ''; d.classList.remove('op-ok');
    });
    grille.appendChild(d);
  }

  function construire() {
    var n = nbChamps();
    if (!n) return;
    css();
    if (!racine) {
      racine = document.createElement('div'); racine.id = 'origin-photos';
      var bouton = form.querySelector('button[type=submit],input[type=submit]') || form.querySelector('button');
      var ancre = bouton ? (bouton.closest('.form-group,.field,.row,div') || bouton) : null;
      if (ancre && ancre.parentNode && form.contains(ancre)) ancre.parentNode.insertBefore(racine, ancre);
      else form.appendChild(racine);
    }
    racine.innerHTML = '<h3>Tes photos <span style="opacity:.6;font-weight:400">(facultatif)</span></h3>' +
      '<p class="op-sub">Elles personnalisent ton livret : couverture et portraits. Tu n’as pas tout sous la main ? Ce n’est pas grave, ' +
      'ajoute seulement celles que tu as, ou aucune : ton livret est livré normalement.</p>' +
      '<div class="op-grille"></div><p class="op-msg" role="status"></p>';
    var g = racine.querySelector('.op-grille');
    for (var i = 1; i <= n; i++) ajouterCase(g, 'photo' + i, prenom(i), false);
    if (n >= 2) ajouterCase(g, 'photo_groupe', n === 2 ? 'Vous deux' : 'Tout le monde', true);
  }

  function majNoms() {
    if (!racine) return;
    qsa('.op-case', racine).forEach(function (c) {
      var m = /^photo(\d+)$/.exec(c.getAttribute('data-cle'));
      if (m) c.querySelector('.op-nom').textContent = prenom(+m[1]);
    });
  }

  // ── Jonction avec l'envoi existant (sans toucher au code du formulaire) ──
  function jointes() {
    var o = {};
    Object.keys(photos).forEach(function (k) { o[k] = photos[k]; });
    return o;
  }
  function estLivret(texte) { return typeof texte === 'string' && texte.indexOf('"prenom1"') !== -1; }

  var fetchOrig = window.fetch;
  if (fetchOrig) {
    window.fetch = function (url, opts) {
      try {
        var p = sansPhotos ? {} : jointes();
        if (opts && Object.keys(p).length && opts.body) {
          if (estLivret(opts.body)) {
            var sans = opts;
            var obj = JSON.parse(opts.body);
            Object.keys(p).forEach(function (k) { obj[k] = p[k]; });
            var avec = Object.assign({}, opts, { body: JSON.stringify(obj) });
            if (sansPhotos) return fetchOrig.call(this, url, sans);
            return fetchOrig.call(this, url, avec).then(function (r) {
              // seul un refus pour taille (413) est rejoué sans photos ; tout le reste est laissé tel quel au formulaire
              if (r && r.status === 413) { sansPhotos = true; return fetchOrig.call(window, url, sans); }
              return r;
            }, function (err) { sansPhotos = true; throw err; });
          }
          if (typeof FormData !== 'undefined' && opts.body instanceof FormData && opts.body.has('prenom1')) {
            Object.keys(p).forEach(function (k) { opts.body.set(k, p[k]); });
          }
        }
      } catch (e) { /* jamais bloquant */ }
      return fetchOrig.apply(this, arguments);
    };
  }
  var xhrSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function (body) {
    try {
      var p = jointes();
      if (Object.keys(p).length && estLivret(body)) {
        var obj = JSON.parse(body); Object.keys(p).forEach(function (k) { obj[k] = p[k]; });
        body = JSON.stringify(obj);
      }
    } catch (e) { /* jamais bloquant */ }
    return xhrSend.call(this, body);
  };

  function demarrer() {
    var champ = document.querySelector('[name="prenom1"]');
    if (!champ) return;
    form = champ.closest('form') || document.body;
    construire();
    form.addEventListener('input', function (e) {
      if (e.target && /^prenom\d+$/.test(e.target.name || '')) majNoms();
    });
    // champs ajoutés ou retirés dynamiquement (ex. enfants en plus) : on remet les cases à jour
    var dernier = nbChamps();
    new MutationObserver(function () {
      var n = nbChamps();
      if (n !== dernier) { dernier = n; construire(); }
    }).observe(form, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer); else demarrer();
})();
