/* diff tour — report behaviour. No library, no build step.
   Everything here is progressive: with JavaScript off the tour is still a complete,
   readable document with plain-text diffs.

   One rule for the viewed state: `mark()` is the only writer, and after every write it
   runs one full `repaint()`. Every widget that shows viewed state registers a painter that
   reads nothing but the `seen` class on the figures. Nothing polls, nothing listens to
   clicks it did not receive. JS sets classes, attributes and custom properties; the
   stylesheet decides what they look like. */
(function () {
  'use strict';

  var uid = document.documentElement.getAttribute('data-uid') || 'x';

  /* ---- storage. file:// shares one origin across every tour on the machine, so keys
     carry the tour's own uid. Browsers that refuse storage for file origins throw on
     access, so every use is guarded and falls back to memory. ---- */
  var memory = {};
  var store = {
    get: function (k) {
      try { var v = localStorage.getItem(k); if (v !== null) return v; } catch (e) {}
      return Object.prototype.hasOwnProperty.call(memory, k) ? memory[k] : null;
    },
    set: function (k, v) {
      memory[k] = v;
      try { localStorage.setItem(k, v); } catch (e) {}
    },
    remove: function (k) {
      delete memory[k];
      try { localStorage.removeItem(k); } catch (e) {}
    }
  };

  var hunks = [].slice.call(document.querySelectorAll('figure.hunk'));
  var chapters = [].slice.call(document.querySelectorAll('section.chapter'));

  /* ---- theme ---- */
  var themeKey = 'difftour.theme';
  var saved = store.get(themeKey);
  if (saved) document.documentElement.setAttribute('data-theme', saved);

  function toggleTheme() {
    var now = document.documentElement.getAttribute('data-theme');
    if (!now) {
      now = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    var next = now === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    store.set(themeKey, next);
  }

  /* ---- viewed state ----
     The key hashes the hunk's own bytes, not its h17 id, so re-generating the tour after a
     rebase keeps the marks for unchanged hunks. The `seen` class on the figure is the
     runtime truth; storage only persists it. */
  function key(fig) { return 'difftour.' + uid + '.' + fig.getAttribute('data-key'); }
  function stored(fig) { return store.get(key(fig)) === '1'; }
  function seen(fig) { return fig.classList.contains('seen'); }
  function allSeen(figs) { return figs.length > 0 && figs.every(seen); }
  function countSeen(figs) { return figs.filter(seen).length; }

  /* Collapsing is a separate, unpersisted state: the path in a hunk's header toggles it,
     marking sets it, jumping to a hunk clears it. */
  function collapse(fig, on) {
    fig.classList.toggle('collapsed', on);
    var ctl = fig.querySelector('[aria-expanded]');
    if (ctl) ctl.setAttribute('aria-expanded', on ? 'false' : 'true');
  }

  var painters = [];      // each repaints one widget from the `seen` classes; order is irrelevant
  var chapterRecs = [];   // {el, link, figs, done}, in document order

  function repaint() {
    painters.forEach(function (paint) { paint(); });
    var completed = [], remaining = [];
    chapterRecs.forEach(function (rec) {
      if (!rec.figs.length) return;
      var now = allSeen(rec.figs);
      if (now && !rec.done) completed.push(rec);
      if (!now) remaining.push(rec);
      rec.done = now;
    });
    return { completed: completed, remaining: remaining };
  }

  function mark(figs, on) {
    /* The same hunk can be shown in two chapters, so two figures can share a key; a mark
       on one is a mark on both. */
    var keys = {};
    figs.forEach(function (f) { keys[key(f)] = true; });
    Object.keys(keys).forEach(function (k) { if (on) store.set(k, '1'); else store.remove(k); });
    hunks.forEach(function (f) {
      if (!keys[key(f)]) return;
      f.classList.toggle('seen', on);
      collapse(f, on);
    });
    announce(repaint());
  }

  /* ---- each hunk: the path collapses, the button marks ----
     Only the path is the collapse control, never the whole figcaption: it also holds the
     viewed button, and interactive content nested inside something with role="button" is
     unreachable for a screen reader. */
  hunks.forEach(function (fig) {
    fig.classList.toggle('seen', stored(fig));
    var hit = fig.querySelector('figcaption .where');
    if (hit) {
      hit.tabIndex = 0;
      hit.setAttribute('role', 'button');
      hit.setAttribute('aria-expanded', 'true');
      function toggle() { collapse(fig, !fig.classList.contains('collapsed')); }
      hit.addEventListener('click', function (e) {
        if (e.target.closest('a, button')) return;
        var sel = window.getSelection && window.getSelection();
        if (sel && String(sel).length) return;
        toggle();
      });
      hit.addEventListener('keydown', function (e) {
        if (e.target !== hit) return;
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
      });
    }
    /* A viewed hunk opens folded, and so does a skip hunk: the reader was told not to
       read it. The skip hunk is not marked viewed by that. */
    collapse(fig, seen(fig) || fig.getAttribute('data-level') === '0');

    var tools = fig.querySelector('figcaption .tools');
    if (tools) {
      var b = document.createElement('button');
      b.className = 'seen';
      b.type = 'button';
      b.addEventListener('click', function () { mark([fig], !seen(fig)); });
      tools.appendChild(b);
      painters.push(function () {
        var on = seen(fig);
        b.textContent = on ? '✓ viewed' : 'mark viewed';
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }
  });

  /* ---- each beat lists its hunks in the prose column: a heat square that toggles the
     hunk's viewed state, the path that jumps to it, and one button for all of them. The
     list is sticky with the prose, so the reader always sees how far through the beat
     they are. ---- */
  [].slice.call(document.querySelectorAll('section.beat')).forEach(function (beat) {
    var say = beat.querySelector('.say');
    var own = [].slice.call(beat.querySelectorAll('.show figure.hunk'));
    if (!say || !own.length) return;
    var box = document.createElement('div');
    box.className = 'changes';
    var lbl = document.createElement('p');
    lbl.className = 'lbl';
    lbl.textContent = own.length === 1 ? 'One change:' : own.length + ' changes:';
    box.appendChild(lbl);
    var ol = document.createElement('ol');
    var squares = [];
    own.forEach(function (fig) {
      var li = document.createElement('li');
      var sq = document.createElement('button');
      sq.type = 'button';
      sq.className = 'sq l' + (fig.getAttribute('data-level') || '1');
      sq.addEventListener('click', function () { mark([fig], !seen(fig)); });
      var where = fig.querySelector('figcaption .where');
      var loc = document.createElement('a');
      loc.className = 'loc';
      loc.href = '#' + fig.id;
      var code = document.createElement('code');
      code.textContent = where ? where.textContent.trim().split(' · ')[0] : fig.id;
      loc.appendChild(code);
      loc.title = code.textContent;
      sq.title = 'mark ' + code.textContent + ' viewed';
      sq.setAttribute('aria-label', sq.title);
      li.appendChild(sq);
      li.appendChild(loc);
      ol.appendChild(li);
      squares.push({ el: sq, fig: fig });
    });
    box.appendChild(ol);

    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'seen group';
    b.addEventListener('click', function () { mark(own, !allSeen(own)); });
    box.appendChild(b);
    say.appendChild(box);

    painters.push(function () {
      squares.forEach(function (s) {
        s.el.setAttribute('aria-pressed', seen(s.fig) ? 'true' : 'false');
      });
      var all = allSeen(own), n = countSeen(own);
      b.textContent = all
        ? (own.length === 1 ? '✓ viewed' : 'All ' + own.length + ' viewed')
        : (own.length === 1 ? 'Mark viewed' : 'Mark all ' + own.length + ' viewed' + (n ? ' (' + n + ' done)' : ''));
      b.setAttribute('aria-pressed', all ? 'true' : 'false');
    });
  });

  /* ---- navigation, built from the chapters themselves. Each entry carries a stripe down
     its left edge: the chapter's hunks in reading order, each segment as tall as the
     hunk's line count, coloured by level. ---- */
  var nav = document.getElementById('nav');
  var list = nav && nav.querySelector('ol');
  var links = {};
  var LEVEL_VAR = ['var(--line)', 'var(--l1)', 'var(--l2)', 'var(--l3)', 'var(--l4)'];

  function stripe(figs) {
    var sizes = figs.map(function (fig) {
      var code = fig.querySelector('pre > code');
      return code ? Math.max(1, code.textContent.split('\n').length - 1) : 1;
    });
    var total = sizes.reduce(function (a, b) { return a + b; }, 0) || 1;
    var stops = [], at = 0;
    figs.forEach(function (fig, i) {
      var lvl = +(fig.getAttribute('data-level') || '1');
      var from = at, to = at + 100 * sizes[i] / total;
      stops.push(LEVEL_VAR[lvl] + ' ' + from.toFixed(2) + '% ' + to.toFixed(2) + '%');
      at = to;
    });
    var el = document.createElement('span');
    el.className = 'stripe';
    el.setAttribute('aria-hidden', 'true');
    el.style.setProperty('--stripe', 'linear-gradient(to bottom, ' + stops.join(', ') + ')');
    return el;
  }

  if (list) {
    list.innerHTML = '';
    chapters.forEach(function (ch, i) {
      var h2 = ch.querySelector('h2');
      if (!h2) return;
      if (!ch.id) ch.id = 'topic-' + (i + 1);
      var figs = [].slice.call(ch.querySelectorAll('figure.hunk'));
      var num = h2.querySelector('.n');
      var title = h2.querySelector('.t') || h2;
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#' + ch.id;
      a.innerHTML = '<span class="n"></span><span class="t"></span><span class="c"></span>';
      a.querySelector('.n').textContent = num ? num.textContent : String(i + 1);
      a.querySelector('.t').textContent = title.textContent.trim();
      li.appendChild(a);
      /* The whole entry is the chapter's target, not just its title line. */
      li.addEventListener('click', function (e) {
        if (e.target.closest('a')) return;
        a.click();
      });
      /* The entry's share of the sidebar grows with the chapter's size. */
      li.style.setProperty('--share', String(Math.max(1, figs.length)));
      if (figs.length) li.appendChild(stripe(figs));
      list.appendChild(li);
      links[ch.id] = a;
      chapterRecs.push({ el: ch, link: a, num: num ? num.textContent : String(i + 1), figs: figs, done: false });
    });
  }

  painters.push(function () {
    chapterRecs.forEach(function (rec) {
      var c = rec.link.querySelector('.c');
      c.textContent = rec.figs.length ? countSeen(rec.figs) + '/' + rec.figs.length : '';
      rec.link.classList.toggle('done', allSeen(rec.figs));
    });
    var bar = document.querySelector('.progress i');
    if (bar) bar.style.setProperty('--progress', (hunks.length ? 100 * countSeen(hunks) / hunks.length : 0) + '%');
  });

  /* ---- the legend's buttons: one per lower level, marking every hunk of that level
     viewed (or, when all of them already are, unmarking them). A reader who wants a
     skim presses skip, read and note and is left with fishy and hot. ---- */
  [].slice.call(document.querySelectorAll('.legend button.level')).forEach(function (b) {
    var lvl = b.getAttribute('data-level');
    var own = hunks.filter(function (f) { return (f.getAttribute('data-level') || '1') === lvl; });
    b.addEventListener('click', function () { mark(own, !allSeen(own)); });
    painters.push(function () {
      var all = allSeen(own);
      b.textContent = all ? '✓ ' + own.length + ' viewed' : 'Mark ' + own.length + ' viewed';
      b.setAttribute('aria-pressed', all ? 'true' : 'false');
      b.disabled = own.length === 0;
    });
  });

  var reset = nav && nav.querySelector('.reset');
  if (reset) reset.addEventListener('click', function () { mark(hunks, false); });
  var themer = nav && nav.querySelector('.theme');
  if (themer) themer.addEventListener('click', toggleTheme);

  /* ---- finishing a chapter. A reader marking hunks viewed loses track of what is left
     and scrolls up and down to find it. So when the last hunk of a chapter is marked, a
     flash says which chapter is done and how many remain, and the page moves on to the
     next chapter that still has unviewed hunks. When the last one is done, the flash says
     so and the page returns to the top. Only `mark()` announces, so marks restored on
     load never do, and unmarking cannot complete anything. ---- */
  var flashBox, flashTimer;
  function flash(title, line) {
    if (!flashBox) {
      var wrap = document.createElement('div');
      wrap.className = 'flash';
      wrap.setAttribute('role', 'status');
      flashBox = document.createElement('div');
      flashBox.className = 'box';
      /* A click dismisses the card at once. It does not undo the scroll that came with it. */
      flashBox.addEventListener('click', function () {
        clearTimeout(flashTimer);
        wrap.classList.remove('on');
      });
      wrap.appendChild(flashBox);
      document.body.appendChild(wrap);
    }
    flashBox.innerHTML = '<b></b><span></span>';
    flashBox.firstChild.textContent = title;
    flashBox.lastChild.textContent = line;
    flashBox.parentNode.classList.add('on');
    clearTimeout(flashTimer);
    flashTimer = setTimeout(function () { flashBox.parentNode.classList.remove('on'); }, 3000);
  }
  /* A few seconds of falling emoji when the whole tour is done. */
  function party() {
    var wrap = document.createElement('div');
    wrap.className = 'party';
    wrap.setAttribute('aria-hidden', 'true');
    var glyphs = ['🥳', '🎉', '👏', '🎈', '🍻', '⭐', '🎊', '✨'];
    for (var i = 0; i < 40; i++) {
      var g = document.createElement('span');
      g.textContent = glyphs[i % glyphs.length];
      g.style.setProperty('--x', (Math.random() * 100) + 'vw');
      g.style.setProperty('--delay', (Math.random() * 1.2) + 's');
      g.style.setProperty('--dur', (2.2 + Math.random() * 1.3) + 's');
      g.style.setProperty('--size', (22 + Math.random() * 18) + 'px');
      wrap.appendChild(g);
    }
    document.body.appendChild(wrap);
    setTimeout(function () { wrap.remove(); }, 4000);
  }
  function announce(delta) {
    if (!delta.completed.length) return;
    if (!delta.remaining.length) {
      flash('All chapters done', 'Tour completed');
      party();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    var last = delta.completed[delta.completed.length - 1];
    flash('Chapter ' + last.num + ' done', delta.remaining.length + ' remaining');
    /* The next unfinished chapter after this one, wrapping around to the first. */
    var i = chapterRecs.indexOf(last), next = null;
    for (var k = 1; k <= chapterRecs.length && !next; k++) {
      var c = chapterRecs[(i + k) % chapterRecs.length];
      if (delta.remaining.indexOf(c) !== -1) next = c;
    }
    if (next) next.el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* First paint: every widget shows the restored state, every chapter record learns
     whether it is already done. Nothing is announced, because nothing was marked. */
  repaint();

  /* ---- which chapter am I in ---- */
  if (window.IntersectionObserver && chapters.length) {
    var visible = {};
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
      var current = null;
      for (var i = 0; i < chapters.length; i++) {
        if (visible[chapters[i].id]) current = chapters[i].id;
      }
      Object.keys(links).forEach(function (id) {
        var li = links[id].parentNode;
        if (id === current) li.setAttribute('aria-current', 'true');
        else li.removeAttribute('aria-current');
      });
      if (current && links[current]) {
        var a = links[current], box = list.getBoundingClientRect(), r = a.getBoundingClientRect();
        if (r.top < box.top || r.bottom > box.bottom) {
          a.scrollIntoView({ block: 'nearest' });
        }
      }
    }, { rootMargin: '-10% 0px -70% 0px' });
    chapters.forEach(function (ch) { spy.observe(ch); });
  }

  /* ---- highlight lazily. A 200-hunk tour should open instantly rather than
     tokenising code nobody has scrolled to. ---- */
  var blocks = [].slice.call(document.querySelectorAll('pre.diff > code'));

  function light(el) {
    if (el.classList.contains('highlighted')) return;
    el.classList.add('highlighted');
    if (window.Prism) {
      try { Prism.highlightElement(el); } catch (e) {}
    }
  }

  if (window.IntersectionObserver) {
    var near = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        obs.unobserve(e.target);
        light(e.target);
      });
    }, { rootMargin: '900px 0px' });
    blocks.forEach(function (el) { near.observe(el); });
  } else {
    blocks.forEach(light);
  }

  /* Jumping to a hunk should highlight it even if it is far below the fold, and open
     it if it was collapsed. */
  function lightAt(hash) {
    if (!hash || hash.length < 2) return;
    var t = document.getElementById(hash.slice(1));
    if (!t) return;
    if (t.matches('figure.hunk')) collapse(t, false);
    [].slice.call(t.querySelectorAll('pre > code')).forEach(light);
  }
  addEventListener('hashchange', function () { lightAt(location.hash); });
  lightAt(location.hash);
})();
