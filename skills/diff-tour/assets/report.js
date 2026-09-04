/* diff tour — report behaviour. No library, no build step.
   Everything here is progressive: with JavaScript off the tour is still a complete,
   readable document with plain-text diffs. */
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

  /* ---- viewed state. The key hashes the hunk's own bytes, not its h17 id, so
     re-generating the tour after a rebase keeps the marks for unchanged hunks. ---- */
  function key(fig) { return 'difftour.' + uid + '.' + fig.getAttribute('data-key'); }
  function isSeen(fig) { return store.get(key(fig)) === '1'; }

  function paint(fig) {
    var on = fig.classList.contains('seen');
    var b = fig.querySelector('button.seen');
    if (b) {
      b.textContent = on ? '✓ viewed' : 'mark viewed';
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    }
  }

  function collapse(fig, on) {
    fig.classList.toggle('collapsed', on);
    var ctl = fig.querySelector('[aria-expanded]');
    if (ctl) ctl.setAttribute('aria-expanded', on ? 'false' : 'true');
  }

  function setSeen(fig, on) {
    var k = key(fig);
    if (on) store.set(k, '1'); else store.remove(k);
    /* The same hunk can be shown in two topics, so two figures can share a key. */
    hunks.forEach(function (other) {
      if (key(other) !== k) return;
      other.classList.toggle('seen', on);
      collapse(other, on);
      paint(other);
    });
    counts();
    scheduleSettle();
  }

  /* The path in the header bar collapses the diff. Only the path, never the whole
     figcaption: it also holds the viewed button, and interactive content nested inside
     something with role="button" is unreachable for a screen reader. */
  hunks.forEach(function (fig) {
    var hit = fig.querySelector('figcaption .where');
    if (!hit) return;
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

    var tools = fig.querySelector('figcaption .tools');
    var b = document.createElement('button');
    b.className = 'seen';
    b.type = 'button';
    b.addEventListener('click', function () { setSeen(fig, !fig.classList.contains('seen')); });
    tools.appendChild(b);
    if (isSeen(fig)) { fig.classList.add('seen'); collapse(fig, true); }
    /* A skip hunk opens folded: the reader was told not to read it. Not marked viewed. */
    else if (fig.getAttribute('data-level') === '0') collapse(fig, true);
    paint(fig);
  });

  /* ---- each beat lists its hunks in the prose column: a heat square, the path, and one
     button that marks them all viewed. The list is sticky with the prose, so the reader
     always sees how far through the beat they are. ---- */
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
    own.forEach(function (fig) {
      var li = document.createElement('li');
      var lvl = fig.getAttribute('data-level') || '1';
      var sq = document.createElement('button');
      sq.type = 'button';
      sq.className = 'sq l' + lvl;
      sq.setAttribute('data-for', fig.id);
      sq.addEventListener('click', function () { setSeen(fig, !fig.classList.contains('seen')); });
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
    });
    box.appendChild(ol);

    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'seen group';
    function allSeen() {
      return own.every(function (f) { return f.classList.contains('seen'); });
    }
    function paintGroup() {
      var n = own.filter(function (f) { return f.classList.contains('seen'); }).length;
      b.textContent = allSeen()
        ? (own.length === 1 ? '✓ viewed' : 'All ' + own.length + ' viewed')
        : (own.length === 1 ? 'Mark viewed' : 'Mark all ' + own.length + ' viewed' + (n ? ' (' + n + ' done)' : ''));
      b.setAttribute('aria-pressed', allSeen() ? 'true' : 'false');
    }
    b.addEventListener('click', function () {
      var to = !allSeen();
      own.forEach(function (f) { setSeen(f, to); });
      paintGroup();
    });
    document.addEventListener('click', function () { setTimeout(paintGroup, 0); });
    paintGroup();
    box.appendChild(b);
    say.appendChild(box);
  });

  /* ---- navigation, built from the chapters themselves. Each entry carries a stripe down
     its left edge: the chapter's hunks in reading order, each segment as tall as the
     hunk's line count, coloured by level. ---- */
  var nav = document.getElementById('nav');
  var list = nav && nav.querySelector('ol');
  var links = {};
  var LEVEL_VAR = ['var(--line)', 'var(--l1)', 'var(--l2)', 'var(--l3)', 'var(--l4)'];

  function stripe(ch) {
    var figs = [].slice.call(ch.querySelectorAll('figure.hunk'));
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
    el.style.background = 'linear-gradient(to bottom, ' + stops.join(', ') + ')';
    return el;
  }

  if (list) {
    list.innerHTML = '';
    chapters.forEach(function (ch, i) {
      var h2 = ch.querySelector('h2');
      if (!h2) return;
      if (!ch.id) ch.id = 'topic-' + (i + 1);
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
      li.style.cursor = 'pointer';
      li.addEventListener('click', function (e) {
        if (e.target.closest('a')) return;
        a.click();
      });
      var n = ch.querySelectorAll('figure.hunk').length;
      /* The entry's share of the sidebar grows with the chapter's size. */
      li.style.flexGrow = String(Math.max(1, n));
      if (n) li.appendChild(stripe(ch));
      list.appendChild(li);
      links[ch.id] = a;
    });
  }

  /* A square shows a tick once its hunk is marked viewed. */
  function paintStrips() {
    [].slice.call(document.querySelectorAll('.changes .sq')).forEach(function (sq) {
      var fig = document.getElementById(sq.getAttribute('data-for'));
      sq.classList.toggle('seen', !!(fig && fig.classList.contains('seen')));
    });
  }

  function counts() {
    var seen = 0;
    chapters.forEach(function (ch) {
      var own = [].slice.call(ch.querySelectorAll('figure.hunk'));
      var n = own.filter(function (f) { return f.classList.contains('seen'); }).length;
      seen += n;
      var a = links[ch.id];
      if (!a) return;
      a.querySelector('.c').textContent = own.length ? n + '/' + own.length : '';
      a.classList.toggle('done', own.length > 0 && n === own.length);
    });
    var bar = document.querySelector('.progress i');
    if (bar) bar.style.width = hunks.length ? (100 * seen / hunks.length) + '%' : '0';
    paintStrips();
  }
  counts();

  /* ---- finishing a chapter. A reader marking hunks viewed loses track of what is left
     and scrolls up and down to find it. So when the last hunk of a chapter is marked, a
     flash says which chapter is done and how many remain, and the page moves on to the
     next chapter that still has unviewed hunks. When the last one is done, the flash says
     so and the page returns to the top. Only a mark made by the reader fires this, never
     the marks restored on load. ---- */
  function chapterDone(ch) {
    var own = [].slice.call(ch.querySelectorAll('figure.hunk'));
    return own.length > 0 && own.every(function (f) { return f.classList.contains('seen'); });
  }
  function doneSet() {
    var set = {};
    chapters.forEach(function (ch) { if (chapterDone(ch)) set[ch.id] = true; });
    return set;
  }
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
      g.style.left = (Math.random() * 100) + 'vw';
      g.style.animationDelay = (Math.random() * 1.2) + 's';
      g.style.animationDuration = (2.2 + Math.random() * 1.3) + 's';
      g.style.fontSize = (22 + Math.random() * 18) + 'px';
      wrap.appendChild(g);
    }
    document.body.appendChild(wrap);
    setTimeout(function () { wrap.remove(); }, 4000);
  }
  var wasDone = doneSet(), settling = false, ready = false;
  function settle() {
    settling = false;
    var now = doneSet();
    var newly = chapters.filter(function (ch) { return now[ch.id] && !wasDone[ch.id]; });
    wasDone = now;
    if (!ready || !newly.length) return;
    var withHunks = chapters.filter(function (ch) { return ch.querySelector('figure.hunk'); });
    var remaining = withHunks.filter(function (ch) { return !now[ch.id]; });
    if (!remaining.length) {
      flash('All chapters done', 'Tour completed');
      party();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    var last = newly[newly.length - 1];
    var num = last.querySelector('h2 .n');
    flash('Chapter ' + (num ? num.textContent : '') + ' done',
          remaining.length + (remaining.length === 1 ? ' remaining' : ' remaining'));
    /* The next unfinished chapter after this one, wrapping around to the first. */
    var i = chapters.indexOf(last), next = null;
    for (var k = 1; k <= chapters.length && !next; k++) {
      var c = chapters[(i + k) % chapters.length];
      if (remaining.indexOf(c) !== -1) next = c;
    }
    if (next) next.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function scheduleSettle() {
    if (settling) return;
    settling = true;
    setTimeout(settle, 0);
  }

  /* ---- the legend's buttons: one per lower level, marking every hunk of that level
     viewed (or, when all of them already are, unmarking them). A reader who wants a
     skim presses skip, read and note and is left with fishy and hot. ---- */
  [].slice.call(document.querySelectorAll('.legend button.level')).forEach(function (b) {
    var lvl = b.getAttribute('data-level');
    var own = hunks.filter(function (f) { return (f.getAttribute('data-level') || '1') === lvl; });
    function allSeen() {
      return own.length > 0 && own.every(function (f) { return f.classList.contains('seen'); });
    }
    function paintLevel() {
      var on = allSeen();
      b.textContent = on ? '✓ ' + own.length + ' viewed'
                         : 'Mark ' + own.length + ' viewed';
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.disabled = own.length === 0;
    }
    b.addEventListener('click', function () {
      var to = !allSeen();
      own.forEach(function (f) { setSeen(f, to); });
      paintLevel();
    });
    /* Stay honest when hunks are marked one at a time or the reset is pressed. */
    document.addEventListener('click', function () { setTimeout(paintLevel, 0); });
    paintLevel();
  });

  var reset = nav && nav.querySelector('.reset');
  if (reset) reset.addEventListener('click', function () {
    hunks.forEach(function (f) { setSeen(f, false); });
  });
  var themer = nav && nav.querySelector('.theme');
  if (themer) themer.addEventListener('click', toggleTheme);

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
    t.classList.remove('collapsed');
    [].slice.call(t.querySelectorAll('pre > code')).forEach(light);
  }
  addEventListener('hashchange', function () { lightAt(location.hash); });
  lightAt(location.hash);

  /* Everything above restored state without announcing it; from here on, marks are the
     reader's own and finishing a chapter is worth a flash. */
  wasDone = doneSet();
  ready = true;
})();
