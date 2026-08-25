/* diff tour — report behaviour. No library, no build step.
   Everything here is progressive: with JavaScript off the report is still a
   complete, readable document with plain-text diffs. */
(function () {
  'use strict';

  var uid = document.documentElement.getAttribute('data-uid') || 'x';

  /* ---- storage. file:// shares one origin across every report on the machine,
     so keys carry the report's own uid. Private windows and browsers that refuse
     storage for file origins throw on access, so every use is guarded and falls
     back to memory for the session. ---- */
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

  var hunks = [].slice.call(document.querySelectorAll('figure.hunk[data-code]'));
  var figures = [].slice.call(document.querySelectorAll('figure.hunk'));
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

  /* ---- viewed state. The key hashes the hunk's own bytes, not its 3.2 code, so
     rewriting narration or reordering chapters keeps the marks and a changed diff
     drops them. ---- */
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
  }

  function setSeen(fig, on) {
    var k = key(fig);
    if (on) store.set(k, '1'); else store.remove(k);
    /* The same fragment can be shown in two chapters, so two figures can share a
       key. Keep every one of them in step rather than assuming keys are unique. */
    hunks.forEach(function (other) {
      if (key(other) !== k) return;
      other.classList.toggle('seen', on);
      paint(other);
    });
    counts();
  }

  /* Collapsing is for every block, including a quote, which has no viewed mark.
     The caption is not a button, so it needs a tabindex and the keys a button
     would have handled. */
  figures.forEach(function (fig) {
    var cap = fig.querySelector('figcaption');
    if (!cap) return;
    cap.tabIndex = 0;
    cap.setAttribute('role', 'button');

    function toggle() { collapse(fig, !fig.classList.contains('collapsed')); }

    cap.addEventListener('click', function (e) {
      if (e.target.closest('a, button')) return;
      /* A drag that selected text is not a click. */
      var sel = window.getSelection && window.getSelection();
      if (sel && String(sel).length) return;
      toggle();
    });
    cap.addEventListener('keydown', function (e) {
      if (e.target !== cap) return;
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });

    if (fig.closest('.beat.fold')) collapse(fig, true);
  });

  hunks.forEach(function (fig) {
    var tools = fig.querySelector('figcaption .tools');
    if (!tools) return;
    var b = document.createElement('button');
    b.className = 'seen';
    b.type = 'button';
    b.addEventListener('click', function () { setSeen(fig, !fig.classList.contains('seen')); });
    tools.appendChild(b);
    if (isSeen(fig)) fig.classList.add('seen');
    paint(fig);
  });

  /* ---- navigation, built from the chapters themselves so the report's own
     markup stays minimal ---- */
  var nav = document.getElementById('nav');
  var list = nav && nav.querySelector('ol');
  var links = {};

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
      list.appendChild(li);
      links[ch.id] = a;
    });
  }

  function counts() {
    var seen = 0;
    chapters.forEach(function (ch) {
      var own = [].slice.call(ch.querySelectorAll('figure.hunk[data-code]'));
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
  }
  counts();

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
      /* When two chapters straddle the reading band, the later one's heading has
         just come into it — that is the one being read, so take the last, not the
         first. */
      var current = null;
      for (var i = 0; i < chapters.length; i++) {
        if (visible[chapters[i].id]) current = chapters[i].id;
      }
      Object.keys(links).forEach(function (id) {
        if (id === current) links[id].setAttribute('aria-current', 'true');
        else links[id].removeAttribute('aria-current');
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

  /* ---- highlight lazily. A 200-hunk report should open instantly rather than
     tokenising code nobody has scrolled to. ---- */
  var blocks = [].slice.call(document.querySelectorAll('pre.diff > code, pre.code > code'));

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

  /* Jumping to a hunk should highlight it even if it is far below the fold. */
  function lightAt(hash) {
    if (!hash || hash.length < 2) return;
    var t = document.getElementById(hash.slice(1));
    if (t) [].slice.call(t.querySelectorAll('pre > code')).forEach(light);
  }
  addEventListener('hashchange', function () { lightAt(location.hash); });
  lightAt(location.hash);
})();
