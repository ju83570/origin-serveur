/* ORIGIN -- écran d'ouverture du site : hyperespace, impact et ralenti, anneau en coup de fouet,
   rayons de lumière depuis la paume, lettres formées de particules d'or.
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

  /* ORIGIN reveal engine v3: warp, impact, bullet time, whip ring, god rays, letters from gold particles.
     OriginEngine(canvas, image) -> { layout(w, h, fit), prepare(), render(t), END, FADE }
     originScore(audioContext, destination, startAt) schedules the matching soundtrack. */
  function OriginEngine(cv, img) {
    var LW = 1220, LH = 970, CX = 610, CY = 490, R = 410, PALM = { x: 575, y: 650 };
    var LETTERS = [['O', 152.5], ['R', 379], ['I', 539], ['G', 729.5], ['I', 903], ['N', 1088.5]], BASE = 560, CAP = 146;
    var MOTTO = '"Comprends ta vie, éclaire ton chemin"', MOTTO_X = 623.5, MOTTO_Y = 711, MOTTO_W = 622;
    var T_IMPACT = 1.95, T_WHIP = 3.35, T_FLARE = 3.95, T_DAWN = 4.2, T_PART = 5.8, T_SNAP = 7.36;
    var g = cv.getContext('2d');
    function mk(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
    var off = mk(LW, LH), o = off.getContext('2d');
    // god-ray buffer covers the logo plus a wide margin so rays can leave the frame
    var RX0 = -1000, RY0 = -1100, RW = LW + 2000, RH = LH + 2200, RS = .16;
    var ray = mk(Math.round(RW * RS), Math.round(RH * RS)), rg = ray.getContext('2d');
    var ray2 = mk(ray.width, ray.height), rg2 = ray2.getContext('2d');
    var txt, tg, tmp, tp, chan, ch, grain, TS = 1, FIT = .8, fs = 200, mfs = 40, parts = [];

    function clamp(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
    function seg(t, a, b) { return clamp((t - a) / (b - a)); }
    function ease(x) { return 1 - Math.pow(1 - clamp(x), 3); }
    function io(x) { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
    function hash(n) { var s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
    function imp(t, at, k) { return t < at ? 0 : Math.exp(-(t - at) * k); }

    // ---- time remap: the scene clock runs fast, freezes into bullet time, snaps back ----
    var SK = [[0, 1], [T_IMPACT, 1], [T_IMPACT + .04, .1], [3.1, .1], [T_WHIP, 1], [T_PART, 1], [6.5, 1.3], [6.85, .15], [7.3, .15], [T_SNAP, 1], [60, 1]];
    function spd(t) {
      for (var i = 1; i < SK.length; i++) if (t <= SK[i][0]) {
        var a = SK[i - 1], b = SK[i]; return a[1] + (b[1] - a[1]) * (t - a[0]) / (b[0] - a[0]);
      }
      return 1;
    }
    var DT = 1 / 200, SC = [0];
    for (var i = 1; i <= 60 / DT; i++) SC.push(SC[i - 1] + spd((i - .5) * DT) * DT);
    function S(t) {
      if (t <= 0) return t;
      var f = t / DT, i = Math.floor(f);
      if (i >= SC.length - 1) return SC[SC.length - 1] + (t - 60);
      return SC[i] + (SC[i + 1] - SC[i]) * (f - i);
    }

    // ---- sizing ------------------------------------------------------------------
    function layout(w, h, fit) {
      cv.width = Math.max(2, w); cv.height = Math.max(2, h);
      FIT = fit || (w > h ? .8 : .94);
      var sc = Math.min(cv.width / LW, cv.height / LH) * FIT;
      TS = Math.min(3, Math.max(1, sc * 1.1));
      txt = mk(Math.round(LW * TS), Math.round(LH * TS)); tg = txt.getContext('2d');
      tmp = mk(cv.width, cv.height); tp = tmp.getContext('2d');
      chan = mk(cv.width, cv.height); ch = chan.getContext('2d');
    }
    function scale() { return Math.min(cv.width / LW, cv.height / LH) * FIT; }

    // fonts must be loaded: measures the type and samples the letters into particle targets
    function prepare() {
      g.font = '400 100px Cinzel, Georgia, serif'; fs = CAP / (g.measureText('I').actualBoundingBoxAscent / 100 || .7);
      g.font = 'italic 400 40px "Cormorant Garamond", Georgia, serif'; mfs = 40 * MOTTO_W / g.measureText(MOTTO).width;
      var c = mk(LW, LH), x = c.getContext('2d');
      x.fillStyle = '#fff'; x.textAlign = 'center'; x.font = '400 ' + fs + 'px Cinzel, Georgia, serif';
      LETTERS.forEach(function (l) { x.fillText(l[0], l[1], BASE); });
      var d = x.getImageData(0, BASE - CAP - 20, LW, CAP + 40).data, n = 0;
      parts = [];
      for (var y = 0; y < CAP + 40; y += 3) for (var xx = 0; xx < LW; xx += 3) {
        if (d[(y * LW + xx) * 4 + 3] < 140) continue;
        var tx = xx, ty = y + BASE - CAP - 20, li = 0, best = 1e9;
        LETTERS.forEach(function (l, k) { var dd = Math.abs(l[1] - tx); if (dd < best) { best = dd; li = k; } });
        var a = hash(n * 3.1) * Math.PI * 2, sx = CX + Math.cos(a) * R, sy = CY + Math.sin(a) * R;
        var mx = (sx + tx) / 2, my = (sy + ty) / 2, px = -(ty - sy), py = tx - sx, pl = Math.hypot(px, py) || 1, bend = (hash(n * 7.7) - .5) * 520;
        parts.push({ tx: tx, ty: ty, sx: sx, sy: sy, cx: mx + px / pl * bend, cy: my + py / pl * bend, d: li * .05 + hash(n * 1.3) * .2, lx: LETTERS[li][1] });
        n++;
      }
      grain = mk(160, 160);
      var gx = grain.getContext('2d'), gd = gx.createImageData(160, 160);
      for (var k = 0; k < gd.data.length; k += 4) { var v = hash(k * .37) * 255; gd.data[k] = gd.data[k + 1] = gd.data[k + 2] = v; gd.data[k + 3] = 255; }
      gx.putImageData(gd, 0, 0);
    }

    // ---- layers (logo space) -----------------------------------------------------
    function ring(alpha, sweep) {
      o.globalCompositeOperation = 'source-over'; o.clearRect(0, 0, LW, LH);
      var a0 = -Math.PI / 2, a1 = a0 + Math.PI * 2 * sweep;
      var gr = o.createRadialGradient(CX, CY, R - 16, CX, CY, R + 90);
      gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(.1, '#000'); gr.addColorStop(.22, '#000');
      gr.addColorStop(.55, 'rgba(0,0,0,.45)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
      o.fillStyle = gr; o.beginPath(); o.moveTo(CX, CY); o.arc(CX, CY, R + 90, a0, a1); o.closePath(); o.fill();
      o.globalCompositeOperation = 'source-in'; o.drawImage(img, 0, 0);
      g.save(); g.globalAlpha = alpha; g.drawImage(off, 0, 0); g.restore();
    }
    function dawn(r) { // leaves the lit image in `off` for the god rays
      o.globalCompositeOperation = 'source-over'; o.clearRect(0, 0, LW, LH);
      var gr = o.createRadialGradient(PALM.x, PALM.y, 0, PALM.x, PALM.y, Math.max(1, r));
      gr.addColorStop(0, '#000'); gr.addColorStop(.45, '#000'); gr.addColorStop(1, 'rgba(0,0,0,0)');
      o.fillStyle = gr; o.fillRect(0, 0, LW, LH);
      o.globalCompositeOperation = 'source-in'; o.drawImage(img, 0, 0);
      g.drawImage(off, 0, 0);
    }
    function godRays(k) { // radial blur of the lit hand from the palm, ping-ponged at low resolution
      if (k <= .01) return;
      var px = (PALM.x - RX0) * RS, py = (PALM.y - RY0) * RS;
      rg.globalCompositeOperation = 'source-over'; rg.globalAlpha = 1; rg.clearRect(0, 0, ray.width, ray.height);
      rg.drawImage(off, -RX0 * RS, -RY0 * RS, LW * RS, LH * RS);
      // each pass averages the buffer with a zoomed copy of itself: energy stays constant, streaks lengthen
      [1.06, 1.12, 1.25, 1.5, 2.0].forEach(function (s) {
        rg2.globalCompositeOperation = 'source-over'; rg2.globalAlpha = 1; rg2.filter = 'none';
        rg2.clearRect(0, 0, ray.width, ray.height); rg2.drawImage(ray, 0, 0);
        rg.globalCompositeOperation = 'source-over'; rg.globalAlpha = .5;
        rg.drawImage(ray2, px - px * s, py - py * s, ray.width * s, ray.height * s);
      });
      rg2.clearRect(0, 0, ray.width, ray.height); rg2.filter = 'blur(3px)'; rg2.drawImage(ray, 0, 0); rg2.filter = 'none';
      g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = Math.min(1, .75 * k);
      g.drawImage(ray2, RX0, RY0, RW, RH); g.restore();
    }
    function glow(x, y, s, a, c) {
      if (a <= .002 || s <= 0) return;
      c = c || '255,236,190';
      var gr = g.createRadialGradient(x, y, 0, x, y, s);
      gr.addColorStop(0, 'rgba(255,250,235,' + Math.min(1, a) + ')'); gr.addColorStop(.18, 'rgba(' + c + ',' + Math.min(1, a) * .75 + ')'); gr.addColorStop(1, 'rgba(232,160,60,0)');
      g.save(); g.globalCompositeOperation = 'lighter'; g.fillStyle = gr; g.beginPath(); g.arc(x, y, s, 0, Math.PI * 2); g.fill(); g.restore();
    }
    function streak(x, y, len, a) {
      if (a <= .002) return;
      g.save(); g.globalCompositeOperation = 'lighter'; g.translate(x, y); g.scale(1, .012);
      var gr = g.createRadialGradient(0, 0, 0, 0, 0, len);
      gr.addColorStop(0, 'rgba(255,240,205,' + Math.min(1, a) + ')'); gr.addColorStop(.4, 'rgba(240,190,110,' + Math.min(1, a) * .35 + ')'); gr.addColorStop(1, 'rgba(240,190,110,0)');
      g.fillStyle = gr; g.beginPath(); g.arc(0, 0, len, 0, Math.PI * 2); g.fill(); g.restore();
    }
    function ghosts(a) { // lens-flare ghosts along the axis from the flare through the frame centre
      if (a <= .002) return;
      var sx = CX, sy = CY - R, vx = 0, vy = LH / 2 - sy + 30;
      [[.55, 26, '255,210,140'], [1.25, 70, '140,210,255'], [1.7, 16, '255,230,180'], [2.3, 120, '255,190,110'], [2.9, 40, '150,220,255']].forEach(function (q) {
        var x = sx + vx * q[0], y = sy + vy * q[0], gr = g.createRadialGradient(x, y, q[1] * .6, x, y, q[1]);
        gr.addColorStop(0, 'rgba(' + q[2] + ',' + a * .05 + ')'); gr.addColorStop(.85, 'rgba(' + q[2] + ',' + a * .16 + ')'); gr.addColorStop(1, 'rgba(' + q[2] + ',0)');
        g.save(); g.globalCompositeOperation = 'lighter'; g.fillStyle = gr; g.beginPath(); g.arc(x, y, q[1], 0, Math.PI * 2); g.fill(); g.restore();
      });
    }
    function warp(t) { // stars rushing at the camera, accelerating, with a twist
      if (t > T_IMPACT) return;
      var u = seg(t, .25, T_IMPACT), W = .25 * u + 2.4 * u * u * u, Wp = .25 * Math.max(0, u - .025) + 2.4 * Math.pow(Math.max(0, u - .025), 3);
      var fade = ease(seg(t, 0, .6));
      g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
      for (var i = 0; i < 520; i++) {
        var r0 = .04 + hash(i) * 1.3, a0 = hash(i + 900) * Math.PI * 2, z0 = hash(i + 1800);
        var z = ((z0 - W) % 1 + 1) % 1 * .98 + .02, zp = Math.min(1, z + (W - Wp));
        var tw = .5 * W, a = a0 + tw;
        var x1 = CX + Math.cos(a) * r0 / z * 150, y1 = CY + Math.sin(a) * r0 / z * 150;
        var x0 = CX + Math.cos(a0 + .5 * Wp) * r0 / zp * 150, y0 = CY + Math.sin(a0 + .5 * Wp) * r0 / zp * 150;
        var al = fade * (1 - z) * .9;
        g.strokeStyle = 'rgba(255,' + (210 + (i % 3) * 15) + ',' + (140 + (i % 5) * 20) + ',' + al + ')';
        g.lineWidth = .8 + (1 - z) * 2.6;
        g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1 + .01, y1); g.stroke();
      }
      g.restore();
      // the core: swells, then is sucked in just before the impact
      var core = 8 + 150 * Math.pow(u, 3), suck = seg(t, 1.72, T_IMPACT);
      core = core * (1 - .92 * ease(suck));
      glow(CX, CY, core * (1 + .15 * Math.sin(t * 40)), .35 + .65 * u);
      streak(CX, CY, 300 * u * (1 - suck * .7), .5 * u);
    }
    function impact(t) {
      if (t < T_IMPACT || t > 4.6) return;
      var sc = S(t) - S(T_IMPACT);
      // shockwave
      var rs = 30 + 1800 * (1 - Math.exp(-2.2 * sc)), a = (1 - seg(sc, 0, .55)) * (1 - seg(t, 3.35, 3.7));
      if (a > 0) {
        g.save(); g.globalCompositeOperation = 'lighter';
        [[60, .08], [22, .18], [6, .55], [2, .9]].forEach(function (w) {
          g.strokeStyle = 'rgba(255,220,160,' + a * w[1] + ')'; g.lineWidth = w[0]; g.beginPath(); g.arc(CX, CY, rs, 0, Math.PI * 2); g.stroke();
        });
        g.restore();
      }
      // debris hanging in bullet time, then flung away when time resumes
      var fade = 1 - seg(sc, .45, 1.05), sp = spd(t);
      if (fade <= 0) return;
      g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
      for (var i = 0; i < 240; i++) {
        var an = hash(i * 2.3) * Math.PI * 2, v = 160 + Math.pow(hash(i * 5.9), 2) * 1500;
        var dist = v * (1 - Math.exp(-sc)), vel = v * Math.exp(-sc);
        var x = CX + Math.cos(an) * dist, y = CY + Math.sin(an) * dist, len = vel * sp * .05 + 2.5;
        var al = fade * (.35 + .65 * hash(i * 9.1));
        g.strokeStyle = i % 4 ? 'rgba(244,196,110,' + al + ')' : 'rgba(255,248,230,' + al + ')';
        g.lineWidth = 1 + hash(i * 3.3) * 2.4;
        g.beginPath(); g.moveTo(x - Math.cos(an) * len, y - Math.sin(an) * len); g.lineTo(x, y); g.stroke();
      }
      g.restore();
      glow(CX, CY, 140 * (1 - seg(sc, 0, .4)), .8 * (1 - seg(sc, 0, .4)));
    }
    function whip(t) {
      if (t < T_WHIP) return;
      var sw = ease(seg(t, T_WHIP, T_FLARE));
      ring(1, sw);
      if (sw >= 1) return;
      var a1 = -Math.PI / 2 + Math.PI * 2 * sw;
      g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
      for (var k = 0; k < 10; k++) {
        g.strokeStyle = 'rgba(255,228,170,' + (1 - k / 10) * .55 + ')'; g.lineWidth = 9 - k * .6;
        g.beginPath(); g.arc(CX, CY, R, Math.max(-Math.PI / 2, a1 - (k + 1) * .09), a1 - k * .09); g.stroke();
      }
      g.restore();
      var hx = CX + Math.cos(a1) * R, hy = CY + Math.sin(a1) * R;
      glow(hx, hy, 70, 1); streak(hx, hy, 380, .7);
    }
    function embers(t) {
      if (t < T_DAWN) return;
      var s = S(t) - S(T_DAWN);
      g.save(); g.globalCompositeOperation = 'lighter';
      var P = 4.2, N = 52;
      for (var i = 0; i < N; i++) {
        var ph = i * P / N; if (s < ph) continue;
        var cyc = Math.floor((s - ph) / P), age = (s - ph) - cyc * P, k = age / P, sd = i * 31 + cyc * 7;
        var ang = hash(sd) * Math.PI * 2, rad = R + 10 + hash(sd + 1) * 40;
        var x = CX + Math.cos(ang) * rad + (hash(sd + 2) - .5) * 40 * age, y = CY + Math.sin(ang) * rad - (18 + hash(sd + 3) * 30) * age;
        g.fillStyle = 'rgba(244,196,110,' + (.7 * Math.sin(k * Math.PI) * clamp(s / 1.5)) + ')';
        g.beginPath(); g.arc(x, y, .9 + hash(sd + 4) * 2.1, 0, Math.PI * 2); g.fill();
      }
      g.restore();
    }
    function particles(t) {
      if (t < T_PART || t > T_SNAP + .9) return;
      var L = S(t) - S(T_PART), D = 1.15, after = seg(t, T_SNAP, T_SNAP + .85), sp = spd(t);
      g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
      g.strokeStyle = 'rgba(255,214,140,1)';
      g.globalAlpha = after > 0 ? (1 - after) * .9 : .85 * ease(seg(t, T_PART, T_PART + .25));
      g.lineWidth = 2.1;
      g.beginPath();
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i], x, y, x0, y0;
        if (after > 0) {
          var k = ease(after) * .35, cyy = BASE - CAP / 2;
          x = p.tx + (p.tx - p.lx) * k; y = p.ty + (p.ty - cyy) * k - after * 30;
          x0 = x - (p.tx - p.lx) * .02; y0 = y + 1;
        } else {
          var q = io(clamp((L - p.d) / D)), q0 = io(clamp((L - p.d - .035 * sp) / D));
          if (q <= 0) continue;
          x = (1 - q) * (1 - q) * p.sx + 2 * (1 - q) * q * p.cx + q * q * p.tx;
          y = (1 - q) * (1 - q) * p.sy + 2 * (1 - q) * q * p.cy + q * q * p.ty;
          x0 = (1 - q0) * (1 - q0) * p.sx + 2 * (1 - q0) * q0 * p.cx + q0 * q0 * p.tx;
          y0 = (1 - q0) * (1 - q0) * p.sy + 2 * (1 - q0) * q0 * p.cy + q0 * q0 * p.ty;
        }
        g.moveTo(x0, y0); g.lineTo(x + .01, y);
      }
      g.stroke(); g.restore();
    }
    function lettering(t) {
      tg.setTransform(1, 0, 0, 1, 0, 0); tg.clearRect(0, 0, txt.width, txt.height); tg.setTransform(TS, 0, 0, TS, 0, 0);
      var on = t >= T_SNAP;
      if (on) {
        tg.textAlign = 'center'; tg.textBaseline = 'alphabetic'; tg.font = '400 ' + fs + 'px Cinzel, Georgia, serif';
        tg.save(); tg.shadowColor = 'rgba(0,0,0,.85)'; tg.shadowBlur = 22 * TS;
        var gr = tg.createLinearGradient(0, BASE - CAP, 0, BASE);
        gr.addColorStop(0, '#F2D383'); gr.addColorStop(.55, '#D8AC45'); gr.addColorStop(1, '#B88A2F');
        tg.fillStyle = gr;
        LETTERS.forEach(function (l) { tg.fillText(l[0], l[1], BASE); });
        tg.restore();
      }
      tg.font = 'italic 400 ' + mfs + 'px "Cormorant Garamond", Georgia, serif'; tg.textAlign = 'left';
      var x = MOTTO_X - tg.measureText(MOTTO).width / 2;
      MOTTO.split(' ').forEach(function (w, i) {
        var p = ease(seg(t, 7.95 + i * .13, 8.75 + i * .13));
        if (p > 0) {
          tg.save(); tg.globalAlpha = p; if (p < .98) tg.filter = 'blur(' + ((1 - p) * 8 * TS).toFixed(1) + 'px)';
          tg.shadowColor = 'rgba(0,0,0,.9)'; tg.shadowBlur = 14 * TS;
          tg.fillStyle = '#F3ECDD'; tg.fillText(w, x, MOTTO_Y); tg.restore();
        }
        x += tg.measureText(w + ' ').width;
      });
      var sp = seg(t, 9.05, 10.2);
      if (on && sp > 0 && sp < 1) {
        tg.save(); tg.globalCompositeOperation = 'source-atop';
        var sx = -250 + sp * (LW + 500), lg = tg.createLinearGradient(sx - 140, 0, sx + 140, 0);
        lg.addColorStop(0, 'rgba(255,248,225,0)'); lg.addColorStop(.5, 'rgba(255,248,225,' + (.8 * Math.sin(sp * Math.PI)) + ')'); lg.addColorStop(1, 'rgba(255,248,225,0)');
        tg.fillStyle = lg; tg.fillRect(0, BASE - CAP - 30, LW, CAP + 60); tg.restore();
      }
      g.drawImage(txt, 0, 0, LW, LH);
      // over-exposed letters at the snap, cooling down
      var hot = imp(t, T_SNAP, 3.2);
      if (hot > .01) { g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = hot; g.drawImage(txt, 0, 0, LW, LH); g.restore(); }
    }

    // ---- camera & post -------------------------------------------------------------
    function zoom(t) {
      var z = t < T_IMPACT ? .9 + .22 * Math.pow(seg(t, 0, T_IMPACT), 3) : 1.12 - .12 * io(seg(t, T_WHIP, 10.6));
      return z + .14 * imp(t, T_IMPACT, 3) + .03 * imp(t, T_FLARE, 5) + .045 * imp(t, T_SNAP, 6);
    }
    function shake(t) {
      var a = 22 * imp(t, T_IMPACT, 4.5) + 6 * imp(t, T_FLARE, 7) + 14 * imp(t, T_SNAP, 6);
      return [a * (Math.sin(t * 83.1) * .6 + Math.sin(t * 47.3 + 1.3) * .4), a * (Math.sin(t * 71.7 + 2) * .6 + Math.sin(t * 39.9) * .4)];
    }
    function aberration(amt) {
      if (amt < .6) return;
      tp.globalCompositeOperation = 'source-over'; tp.drawImage(cv, 0, 0);
      g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
      g.fillStyle = '#000'; g.fillRect(0, 0, cv.width, cv.height);
      [['#f00', -amt, 0], ['#0f0', 0, 0], ['#00f', amt, amt * .35]].forEach(function (c) {
        ch.globalCompositeOperation = 'source-over'; ch.drawImage(tmp, 0, 0);
        ch.globalCompositeOperation = 'multiply'; ch.fillStyle = c[0]; ch.fillRect(0, 0, cv.width, cv.height);
        g.globalCompositeOperation = 'lighter'; g.drawImage(chan, c[1], c[2]);
      });
      g.globalCompositeOperation = 'source-over';
    }
    function finish(t) {
      var W = cv.width, H = cv.height;
      g.setTransform(1, 0, 0, 1, 0, 0);
      var fl = (t < T_IMPACT ? .65 * Math.pow(seg(t, 1.84, T_IMPACT), 3) : imp(t, T_IMPACT, 5.5)) + .1 * imp(t, T_FLARE, 6) + .3 * imp(t, T_SNAP, 7);
      if (fl > .003) { g.globalCompositeOperation = 'lighter'; g.fillStyle = 'rgba(255,232,190,' + Math.min(1, fl) + ')'; g.fillRect(0, 0, W, H); }
      var u = Math.max(W, H), vg = g.createRadialGradient(W / 2, H / 2, u * .28, W / 2, H / 2, u * .75);
      vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.6)');
      g.globalCompositeOperation = 'source-over'; g.fillStyle = vg; g.fillRect(0, 0, W, H);
      if (grain) {
        g.globalCompositeOperation = 'overlay'; g.globalAlpha = .09;
        var f = Math.floor(t * 24), ox = -Math.floor(hash(f) * 160), oy = -Math.floor(hash(f + 99) * 160), gs = Math.max(1, Math.round(u / 900));
        for (var y = oy; y < H; y += 160 * gs) for (var x = ox; x < W; x += 160 * gs) g.drawImage(grain, x, y, 160 * gs, 160 * gs);
        g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
      }
    }

    function render(t) {
      g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1; g.filter = 'none';
      g.fillStyle = '#000'; g.fillRect(0, 0, cv.width, cv.height);
      if (!img.complete || !txt) return;
      var s = scale() * zoom(t), sh = shake(t), k = cv.height / 1000;
      g.setTransform(s, 0, 0, s, cv.width / 2 - CX * s + sh[0] * k, cv.height / 2 - (LH / 2) * s + sh[1] * k);
      warp(t);
      impact(t);
      whip(t);
      if (t >= T_FLARE) {
        var f = seg(t, T_FLARE, T_FLARE + 1.4), fl = Math.pow(1 - f, 2.2);
        if (f < 1) {
          glow(CX, CY - R, 90 + 280 * ease(f * 1.5), fl); streak(CX, CY - R, 1000 * (.4 + .6 * ease(f * 2)), .95 * fl); ghosts(fl);
          g.save(); g.globalCompositeOperation = 'lighter'; ring(.7 * fl, 1); g.restore();
        }
        g.save(); g.globalCompositeOperation = 'lighter'; ring((.14 + .1 * Math.sin((t - T_FLARE) * 1.5)) * clamp(t - 4.5), 1); g.restore();
      }
      var d = seg(t, T_DAWN, 6.0);
      if (d > 0) {
        dawn(ease(d) * 1250);
        godRays(ease(seg(t, 4.4, 5.3)) * (1 - .62 * seg(t, 5.6, 7.6)) * (1 + .12 * Math.sin(t * 1.7)) + .8 * imp(t, T_SNAP, 2.5));
        if (d >= 1) glow(PALM.x, PALM.y + 20, 260, .06 + .04 * Math.sin((t - 6) * 1.3), '240,170,80');
      }
      embers(t);
      particles(t);
      lettering(t);
      if (t >= T_SNAP) streak(CX, BASE - CAP / 2, 1500, .9 * imp(t, T_SNAP, 3));
      aberration((16 * imp(t, T_IMPACT, 2.5) + 5 * imp(t, T_FLARE, 6) + 11 * imp(t, T_SNAP, 4)) * cv.height / 1080);
      finish(t);
    }

    return { layout: layout, prepare: prepare, render: render, END: 12, FADE: 10.5 };
  }

  var box, cv, E, t0 = 0, raf = 0, fini = false;
  var img = new Image();

  function layout() {
    var d = Math.min(2, window.devicePixelRatio || 1);
    E.layout(Math.round(innerWidth * d), Math.round(innerHeight * d));
  }
  function terminer() {
    if (fini) return;
    fini = true;
    try { sessionStorage.setItem(KEY, '1'); } catch (e) {}
    root.classList.remove('origin-intro-on');
    if (!box) { st.remove(); return; }
    box.classList.add('fin');
    setTimeout(function () {
      cancelAnimationFrame(raf); box.remove(); st.remove();
      removeEventListener('resize', layout); removeEventListener('keydown', touche);
    }, 950);
  }
  function touche(e) { if (e.key === 'Escape') terminer(); }
  function boucle(now) {
    if (!t0) t0 = now;
    var t = (now - t0) / 1000;
    E.render(t);
    if (t >= E.FADE) terminer();
    raf = requestAnimationFrame(boucle);
  }
  function monter() {
    box = document.createElement('div');
    box.id = 'origin-intro';
    box.setAttribute('role', 'img');
    box.setAttribute('aria-label', 'ORIGIN. Comprends ta vie, éclaire ton chemin.');
    cv = document.createElement('canvas');
    E = OriginEngine(cv, img);
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
    E.prepare();
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
