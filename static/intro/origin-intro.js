/* ORIGIN -- écran d'ouverture (éclipse, aube depuis la paume, lettres révélées une à une).
   À placer dans le <head> du site :
     <script src="https://<serveur-origin>/static/intro/origin-intro.js"></script>
   Joué une fois par session de navigation. Passable (clic, bouton, Échap).
   ?intro dans l'URL force la lecture, ?nointro la désactive.
   Fichier lu à côté du script : fond.jpg (le logo sans son texte, le texte est redessiné). */
(function () {
  'use strict';
  var KEY = 'origin-intro-vue';
  var q = location.search;
  var force = /[?&]intro\b/.test(q);
  if (/[?&]nointro\b/.test(q)) return;
  try { if (!force && sessionStorage.getItem(KEY)) return; } catch (e) {}
  if (!force && window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var script = document.currentScript;
  var BASE = script && script.src ? script.src.replace(/[^\/]*(\?.*)?$/, '') : '/static/intro/';
  var root = document.documentElement;

  // Cache le site tout de suite, avant même que le <body> existe.
  var st = document.createElement('style');
  st.textContent =
    'html.origin-intro-on body{visibility:hidden}' +
    'html.origin-intro-on{overflow:hidden}' +
    '#origin-intro{position:fixed;inset:0;z-index:2147483000;background:#000;opacity:1;transition:opacity .9s ease;cursor:pointer}' +
    '#origin-intro.fin{opacity:0;pointer-events:none}' +
    '#origin-intro canvas{position:absolute;inset:0;width:100%;height:100%;display:block}' +
    '#origin-intro button{position:absolute;right:max(20px,env(safe-area-inset-right,0px));bottom:max(20px,env(safe-area-inset-bottom,0px));' +
    'font:500 11px/1 Jost,system-ui,sans-serif;letter-spacing:.3em;text-transform:uppercase;color:#F0C878;background:rgba(0,0,0,.35);' +
    'border:1px solid rgba(201,168,76,.4);border-radius:99px;padding:11px 18px;cursor:pointer;opacity:0;transition:opacity .6s ease .8s,background .3s}' +
    '#origin-intro.pret button{opacity:1}' +
    '#origin-intro button:hover{background:rgba(201,168,76,.12)}' +
    '#origin-intro button:focus-visible{outline:2px solid #F0C878;outline-offset:3px}';
  (document.head || root).appendChild(st);
  root.classList.add('origin-intro-on');
  if (!document.querySelector('link[href*="family=Cinzel"]') || !document.querySelector('link[href*="Cormorant"]')) {
    var lf = document.createElement('link');
    lf.rel = 'stylesheet';
    lf.href = 'https://fonts.googleapis.com/css2?family=Cinzel:wght@400&family=Cormorant+Garamond:ital,wght@1,400&family=Jost:wght@500&display=swap';
    (document.head || root).appendChild(lf);
  }

  var LW = 1220, LH = 970, CX = 610, CY = 490, R = 410, PALM = { x: 575, y: 650 };
  var LETTERS = [['O', 152.5], ['R', 379], ['I', 539], ['G', 729.5], ['I', 903], ['N', 1088.5]], BASE_Y = 560, CAP = 146;
  var MOTTO = '"Comprends ta vie, éclaire ton chemin"', MOTTO_X = 623.5, MOTTO_Y = 711, MOTTO_W = 622;
  var FADE = 9.4;

  var box, cv, g, off, o, txt, tg, TS = 1, fs = 200, mfs = 40, t0 = 0, raf = 0, fini = false;
  var img = new Image();

  function mk(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function clamp(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function seg(t, a, b) { return clamp((t - a) / (b - a)); }
  function ease(x) { return 1 - Math.pow(1 - clamp(x), 3); }
  function io(x) { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
  function hash(n) { var s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }

  function fitScale() { return Math.min(cv.width / LW, cv.height / LH) * (cv.width > cv.height ? .8 : .94); }
  function layout() {
    var d = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.max(2, Math.round(innerWidth * d));
    cv.height = Math.max(2, Math.round(innerHeight * d));
    TS = Math.min(3, Math.max(1, fitScale()));
    txt = mk(Math.round(LW * TS), Math.round(LH * TS)); tg = txt.getContext('2d');
  }
  function view(z) {
    var S = fitScale() * z;
    g.setTransform(S, 0, 0, S, cv.width / 2 - CX * S, cv.height / 2 - (LH / 2) * S);
  }

  function ring(alpha, sweep) {
    o.globalCompositeOperation = 'source-over'; o.clearRect(0, 0, LW, LH);
    var a0 = -Math.PI / 2, a1 = a0 + Math.PI * 2 * sweep;
    var rg = o.createRadialGradient(CX, CY, R - 16, CX, CY, R + 90);
    rg.addColorStop(0, 'rgba(0,0,0,0)'); rg.addColorStop(.1, '#000'); rg.addColorStop(.22, '#000');
    rg.addColorStop(.55, 'rgba(0,0,0,.45)'); rg.addColorStop(1, 'rgba(0,0,0,0)');
    o.fillStyle = rg; o.beginPath(); o.moveTo(CX, CY); o.arc(CX, CY, R + 90, a0, a1); o.closePath(); o.fill();
    o.globalCompositeOperation = 'source-in'; o.drawImage(img, 0, 0);
    g.save(); g.globalAlpha = alpha; g.drawImage(off, 0, 0); g.restore();
  }
  function dawn(r) {
    o.globalCompositeOperation = 'source-over'; o.clearRect(0, 0, LW, LH);
    var rg = o.createRadialGradient(PALM.x, PALM.y, 0, PALM.x, PALM.y, Math.max(1, r));
    rg.addColorStop(0, '#000'); rg.addColorStop(.45, '#000'); rg.addColorStop(1, 'rgba(0,0,0,0)');
    o.fillStyle = rg; o.fillRect(0, 0, LW, LH);
    o.globalCompositeOperation = 'source-in'; o.drawImage(img, 0, 0);
    g.drawImage(off, 0, 0);
  }
  function glow(x, y, s, a, c) {
    if (a <= 0) return;
    c = c || '255,236,190';
    var rg = g.createRadialGradient(x, y, 0, x, y, s);
    rg.addColorStop(0, 'rgba(255,250,235,' + a + ')'); rg.addColorStop(.18, 'rgba(' + c + ',' + a * .75 + ')'); rg.addColorStop(1, 'rgba(232,160,60,0)');
    g.save(); g.globalCompositeOperation = 'lighter'; g.fillStyle = rg; g.beginPath(); g.arc(x, y, s, 0, Math.PI * 2); g.fill(); g.restore();
  }
  function streak(x, y, len, a) {
    if (a <= 0) return;
    g.save(); g.globalCompositeOperation = 'lighter'; g.translate(x, y); g.scale(1, .012);
    var rg = g.createRadialGradient(0, 0, 0, 0, 0, len);
    rg.addColorStop(0, 'rgba(255,240,205,' + a + ')'); rg.addColorStop(.4, 'rgba(240,190,110,' + a * .35 + ')'); rg.addColorStop(1, 'rgba(240,190,110,0)');
    g.fillStyle = rg; g.beginPath(); g.arc(0, 0, len, 0, Math.PI * 2); g.fill(); g.restore();
  }
  function embers(t) {
    if (t < 2.4) return;
    g.save(); g.globalCompositeOperation = 'lighter';
    var P = 4.2, N = 46;
    for (var i = 0; i < N; i++) {
      var ph = 2.4 + i * P / N; if (t < ph) continue;
      var cyc = Math.floor((t - ph) / P), age = (t - ph) - cyc * P, k = age / P, sd = i * 31 + cyc * 7;
      var ang = hash(sd) * Math.PI * 2, rad = R + 10 + hash(sd + 1) * 40;
      var x = CX + Math.cos(ang) * rad + (hash(sd + 2) - .5) * 40 * age, y = CY + Math.sin(ang) * rad - (18 + hash(sd + 3) * 30) * age;
      g.fillStyle = 'rgba(244,196,110,' + (.7 * Math.sin(k * Math.PI) * clamp((t - 2.4) / 1.5)) + ')';
      g.beginPath(); g.arc(x, y, .9 + hash(sd + 4) * 2.1, 0, Math.PI * 2); g.fill();
    }
    g.restore();
  }
  function lettering(t) {
    tg.setTransform(1, 0, 0, 1, 0, 0); tg.clearRect(0, 0, txt.width, txt.height); tg.setTransform(TS, 0, 0, TS, 0, 0);
    tg.textAlign = 'center'; tg.textBaseline = 'alphabetic';
    tg.font = '400 ' + fs + 'px Cinzel, Georgia, serif';
    var blooms = [];
    LETTERS.forEach(function (l, i) {
      var p = ease(seg(t, 4.7 + i * .2, 5.8 + i * .2));
      if (p <= 0) return;
      var dy = (1 - p) * 22, blur = (1 - p) * 14;
      tg.save(); tg.globalAlpha = p;
      if (blur > .3) tg.filter = 'blur(' + (blur * TS).toFixed(1) + 'px)';
      tg.shadowColor = 'rgba(0,0,0,.85)'; tg.shadowBlur = 22 * TS;
      var gr = tg.createLinearGradient(0, BASE_Y - CAP - dy, 0, BASE_Y - dy);
      gr.addColorStop(0, '#F2D383'); gr.addColorStop(.55, '#D8AC45'); gr.addColorStop(1, '#B88A2F');
      tg.fillStyle = gr; tg.fillText(l[0], l[1], BASE_Y + dy);
      tg.restore();
      blooms.push([l[1], p]);
    });
    tg.font = 'italic 400 ' + mfs + 'px "Cormorant Garamond", Georgia, serif'; tg.textAlign = 'left';
    var x = MOTTO_X - tg.measureText(MOTTO).width / 2;
    MOTTO.split(' ').forEach(function (w, i) {
      var p = ease(seg(t, 6.4 + i * .16, 7.3 + i * .16));
      if (p > 0) {
        tg.save(); tg.globalAlpha = p; tg.shadowColor = 'rgba(0,0,0,.9)'; tg.shadowBlur = 14 * TS;
        tg.fillStyle = '#F3ECDD'; tg.fillText(w, x, MOTTO_Y + (1 - p) * 8); tg.restore();
      }
      x += tg.measureText(w + ' ').width;
    });
    var sp = seg(t, 8.1, 9.5);
    if (sp > 0 && sp < 1) {
      tg.save(); tg.globalCompositeOperation = 'source-atop';
      var sx = -250 + sp * (LW + 500), lg = tg.createLinearGradient(sx - 140, 0, sx + 140, 0);
      lg.addColorStop(0, 'rgba(255,248,225,0)'); lg.addColorStop(.5, 'rgba(255,248,225,' + (.75 * Math.sin(sp * Math.PI)) + ')'); lg.addColorStop(1, 'rgba(255,248,225,0)');
      tg.fillStyle = lg; tg.fillRect(0, BASE_Y - CAP - 30, LW, CAP + 60); tg.restore();
    }
    g.drawImage(txt, 0, 0, LW, LH);
    blooms.forEach(function (b) { if (b[1] < 1) glow(b[0], BASE_Y - CAP / 2, 120, .22 * Math.sin(b[1] * Math.PI), '240,190,110'); });
  }
  function render(t) {
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
    g.fillStyle = '#000'; g.fillRect(0, 0, cv.width, cv.height);
    view(1.07 - .07 * io(seg(t, 0, 9.5)));
    var wake = ease(seg(t, .4, 1.4)), sw = io(seg(t, 1.3, 3.2));
    if (sw > 0) ring(1, sw);
    if (wake > 0 && sw < 1) {
      var a = -Math.PI / 2 + Math.PI * 2 * sw, px = CX + Math.cos(a) * R, py = CY + Math.sin(a) * R;
      glow(px, py, (46 + 26 * Math.sin(t * 11)) * (.4 + .6 * wake), wake); streak(px, py, 260 * wake, .55 * wake);
    }
    var f = seg(t, 3.2, 4.6), fl = f > 0 ? Math.pow(1 - f, 2.2) : 0;
    if (f > 0 && f < 1) {
      glow(CX, CY - R, 90 + 260 * ease(f * 1.5), fl); streak(CX, CY - R, 900 * (.4 + .6 * ease(f * 2)), .9 * fl);
      g.save(); g.globalCompositeOperation = 'lighter'; ring(.6 * fl, 1); g.restore();
    }
    var d = seg(t, 3.4, 5.6);
    if (d > 0) dawn(ease(d) * 1250);
    if (sw >= 1) { g.save(); g.globalCompositeOperation = 'lighter'; ring((.14 + .1 * Math.sin((t - 3.2) * 1.5)) * clamp(t - 4), 1); g.restore(); }
    if (d >= 1) glow(PALM.x, PALM.y + 20, 260, .06 + .04 * Math.sin((t - 5.6) * 1.3), '240,170,80');
    embers(t);
    lettering(t);
  }

  function terminer() {
    if (fini) return;
    fini = true;
    try { sessionStorage.setItem(KEY, '1'); } catch (e) {}
    root.classList.remove('origin-intro-on');
    if (!box) { st.remove(); return; }
    box.classList.add('fin');
    setTimeout(function () { cancelAnimationFrame(raf); box.remove(); st.remove(); removeEventListener('resize', layout); removeEventListener('keydown', touche); }, 950);
  }
  function touche(e) { if (e.key === 'Escape') terminer(); }
  function boucle(now) {
    if (!t0) t0 = now;
    var t = (now - t0) / 1000;
    render(t);
    if (t >= FADE) terminer();
    if (!box.classList.contains('fin') || t < FADE + 1) raf = requestAnimationFrame(boucle);
  }
  function monter() {
    box = document.createElement('div');
    box.id = 'origin-intro';
    box.setAttribute('role', 'img');
    box.setAttribute('aria-label', 'ORIGIN. Comprends ta vie, éclaire ton chemin.');
    cv = document.createElement('canvas'); g = cv.getContext('2d');
    off = mk(LW, LH); o = off.getContext('2d');
    var b = document.createElement('button');
    b.type = 'button'; b.textContent = 'Passer';
    b.addEventListener('click', function (e) { e.stopPropagation(); terminer(); });
    box.appendChild(cv); box.appendChild(b);
    box.addEventListener('click', terminer);
    root.appendChild(box);
    layout();
    addEventListener('resize', layout);
    addEventListener('keydown', touche);
  }
  function demarrer() {
    if (fini) return;
    g.font = '400 100px Cinzel, Georgia, serif'; fs = CAP / (g.measureText('I').actualBoundingBoxAscent / 100 || .7);
    g.font = 'italic 400 40px "Cormorant Garamond", Georgia, serif'; mfs = 40 * MOTTO_W / g.measureText(MOTTO).width;
    box.classList.add('pret');
    raf = requestAnimationFrame(boucle);
  }

  monter();
  // Sans image, pas d'intro : on rend le site immédiatement.
  var secours = setTimeout(terminer, 4000);
  img.onerror = function () { clearTimeout(secours); terminer(); };
  img.onload = function () {
    clearTimeout(secours);
    var polices = document.fonts && document.fonts.load
      ? Promise.all([document.fonts.load('400 100px Cinzel'), document.fonts.load('italic 400 40px "Cormorant Garamond"')])
      : Promise.resolve();
    Promise.race([polices, new Promise(function (r) { setTimeout(r, 1500); })]).then(demarrer, demarrer);
  };
  img.src = BASE + 'fond.jpg';
})();
