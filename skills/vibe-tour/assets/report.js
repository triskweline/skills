/* vibe tour — report behaviour. No library, no build step.
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
  var themeKey = 'vibetour.theme';
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
  function key(fig) { return 'vibetour.' + uid + '.' + fig.getAttribute('data-key'); }
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
    paint(fig);
  });

  /* ---- one control for a run of hunks read as a group. A lockfile can be forty
     hunks under one paragraph; four is where clicking one at a time starts to nag. ---- */
  [].slice.call(document.querySelectorAll('section.beat .show')).forEach(function (show) {
    var own = [].slice.call(show.querySelectorAll('figure.hunk'));
    if (own.length < 4) return;
    var bar = document.createElement('div');
    bar.className = 'groupbar';
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'seen group';

    function allSeen() {
      return own.every(function (f) { return f.classList.contains('seen'); });
    }
    function paintGroup() {
      var n = own.filter(function (f) { return f.classList.contains('seen'); }).length;
      b.classList.toggle('seen', allSeen());
      b.textContent = allSeen()
        ? 'All ' + own.length + ' viewed'
        : 'Mark all ' + own.length + ' viewed' + (n ? ' (' + n + ' done)' : '');
      b.setAttribute('aria-pressed', allSeen() ? 'true' : 'false');
    }
    b.addEventListener('click', function () {
      var to = !allSeen();
      own.forEach(function (f) { setSeen(f, to); });
      paintGroup();
    });
    own.forEach(function (f) {
      var ib = f.querySelector('button.seen');
      if (ib) ib.addEventListener('click', paintGroup);
    });
    paintGroup();
    bar.appendChild(b);
    show.insertBefore(bar, show.firstChild);
  });

  /* ---- navigation, built from the chapters themselves. Under each entry sits the
     chapter's heat strip: one square per hunk, in reading order, coloured by attention
     level, each a link to its hunk. The same strip is drawn under the chapter heading
     in the page, larger. ---- */
  var nav = document.getElementById('nav');
  var list = nav && nav.querySelector('ol');
  var links = {};
  var LEVEL_NAME = ['skip', 'read once', 'note', 'fishy', 'hot'];

  function strip(ch) {
    var ol = document.createElement('ol');
    ol.className = 'heat';
    [].slice.call(ch.querySelectorAll('figure.hunk')).forEach(function (fig) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      var lvl = fig.getAttribute('data-level') || '1';
      a.className = 'sq l' + lvl;
      a.href = '#' + fig.id;
      var where = fig.querySelector('figcaption .where');
      var reason = fig.getAttribute('data-reason');
      a.title = LEVEL_NAME[+lvl] + ' · ' + (where ? where.textContent.trim() : fig.id)
              + (reason ? '\n' + reason : '');
      a.setAttribute('aria-label', a.title);
      a.setAttribute('data-for', fig.id);
      li.appendChild(a);
      ol.appendChild(li);
    });
    return ol;
  }

  if (list) {
    list.innerHTML = '';
    chapters.forEach(function (ch, i) {
      var h2 = ch.querySelector('h2');
      if (!h2) return;
      if (!ch.id) ch.id = 'ch' + (i + 1);
      var num = h2.querySelector('.n');
      var title = h2.querySelector('.t') || h2;
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#' + ch.id;
      a.innerHTML = '<span class="n"></span><span class="t"></span><span class="c"></span>';
      a.querySelector('.n').textContent = num ? num.textContent : String(i + 1);
      a.querySelector('.t').textContent = title.textContent.trim();
      li.appendChild(a);
      if (ch.querySelector('figure.hunk')) {
        li.appendChild(strip(ch));
        h2.parentNode.insertBefore(strip(ch), h2.nextSibling);
      }
      list.appendChild(li);
      links[ch.id] = a;
    });
  }

  /* A square dims once its hunk is marked viewed, so the strips double as progress. */
  function paintStrips() {
    [].slice.call(document.querySelectorAll('.heat .sq')).forEach(function (sq) {
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
    var bar = nav && nav.querySelector('.bar i');
    if (bar) bar.style.width = hunks.length ? (100 * seen / hunks.length) + '%' : '0';
    var tally = nav && nav.querySelector('.tally');
    if (tally) tally.textContent = seen + '/' + hunks.length;
    paintStrips();
  }
  counts();

  /* ---- the scrutiny dial. Skim shows only hot and fishy hunks open; review adds
     notes; thorough adds the unmarked hunks; everything opens the skips too. A hunk
     below the threshold is collapsed to its header bar, one click from open, so every
     hunk stays on the page. A hunk the reader marked viewed stays collapsed either way. ---- */
  var DIAL = { skim: 3, review: 2, thorough: 1, everything: 0 };
  var dialKey = 'vibetour.' + uid + '.scrutiny';
  var dial = nav && nav.querySelector('.dial');

  function applyDial(name) {
    var min = DIAL[name];
    if (min === undefined) { name = 'thorough'; min = 1; }
    hunks.forEach(function (fig) {
      if (fig.classList.contains('seen')) return;
      var lvl = fig.getAttribute('data-level');
      collapse(fig, (lvl === null ? 1 : +lvl) < min);
    });
    if (dial) {
      [].slice.call(dial.querySelectorAll('button')).forEach(function (b) {
        b.setAttribute('aria-pressed', b.getAttribute('data-dial') === name ? 'true' : 'false');
      });
    }
    store.set(dialKey, name);
  }
  if (dial) {
    [].slice.call(dial.querySelectorAll('button')).forEach(function (b) {
      b.addEventListener('click', function () { applyDial(b.getAttribute('data-dial')); });
    });
  }
  applyDial(store.get(dialKey) || 'thorough');

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
})();
