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
  /* Octicon-like icons, drawn in the text colour. */
  var ICONS = {
    up: '<path d="M8 2 4.5 5.5h2.25V9h2.5V5.5h2.25z"/><path d="M2 12.5h2M5.5 12.5h2M9 12.5h2M12.5 12.5h1.5" stroke="currentColor" stroke-width="1.5"/>',
    down: '<path d="M8 14l3.5-3.5H9.25V7h-2.5v3.5H4.5z"/><path d="M2 3.5h2M5.5 3.5h2M9 3.5h2M12.5 3.5h1.5" stroke="currentColor" stroke-width="1.5"/>',
    all: '<path d="M8 1 5 4h2v2.5h2V4h2zM8 15l3-3H9V9.5H7V12H5z"/><path d="M2 8h2M5.5 8h2M9 8h2M12.5 8h1.5" stroke="currentColor" stroke-width="1.5"/>',
    fold: '<path d="M8 6.5 5 3.5h2V1h2v2.5h2zM8 9.5l3 3H9V15H7v-2.5H5z"/><path d="M2 8h2M5.5 8h2M9 8h2M12.5 8h1.5" stroke="currentColor" stroke-width="1.5"/>',
    chev: '<path d="M4.5 6 8 9.5 11.5 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
  };
  function icon(name) {
    return '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="currentColor">' + ICONS[name] + '</svg>';
  }
  function iconButton(name, label, onClick) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'icon ' + name;
    b.title = label;
    b.setAttribute('aria-label', label);
    b.innerHTML = icon(name);
    b.addEventListener('click', function (e) { e.stopPropagation(); onClick(); });
    return b;
  }

  function collapse(fig, on) {
    fig.classList.toggle('collapsed', on);
    var ctl = fig.querySelector('[aria-expanded]');
    if (ctl) ctl.setAttribute('aria-expanded', on ? 'false' : 'true');
  }

  var painters = [];      // each repaints one widget from the `seen` classes; order is irrelevant
  var chapterRecs = [];   // {el, link, num, figs, done}, in document order
  var beatRecs = [];      // {el, chapter, figs, done}, in document order; only beats with hunks

  /* Repaint everything, then work out what this change finished: which beats and which
     chapters went from unfinished to finished, and which chapters are still open. */
  function repaint() {
    painters.forEach(function (paint) { paint(); });
    var delta = { beats: [], completed: [], remaining: [] };
    beatRecs.forEach(function (rec) {
      var now = allSeen(rec.figs);
      if (now && !rec.done) delta.beats.push(rec);
      rec.done = now;
    });
    chapterRecs.forEach(function (rec) {
      if (!rec.figs.length) return;
      var now = allSeen(rec.figs);
      if (now && !rec.done) delta.completed.push(rec);
      if (!now) delta.remaining.push(rec);
      rec.done = now;
    });
    return delta;
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
      hit.insertAdjacentHTML('afterbegin', '<span class="chev">' + icon('chev') + '</span>');
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
    beatRecs.push({ el: beat, chapter: beat.closest('section.chapter'), figs: own, done: false });
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

  /* ---- each chapter title carries one button for every hunk in the chapter, across all
     its beats, so a reader who has read a whole topic marks it in one press. ---- */
  chapterRecs.forEach(function (rec) {
    var h2 = rec.el.querySelector(':scope > h2');
    if (!h2 || !rec.figs.length) return;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'seen group';
    b.addEventListener('click', function () { mark(rec.figs, !allSeen(rec.figs)); });
    h2.appendChild(b);
    painters.push(function () {
      var all = allSeen(rec.figs), n = countSeen(rec.figs), total = rec.figs.length;
      b.textContent = all
        ? (total === 1 ? '✓ viewed' : 'All ' + total + ' viewed')
        : (total === 1 ? 'Mark viewed' : 'Mark all ' + total + ' viewed' + (n ? ' (' + n + ' done)' : ''));
      b.setAttribute('aria-pressed', all ? 'true' : 'false');
    });
  });

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
  function flash(title, line, done) {
    if (!flashBox) {
      var wrap = document.createElement('div');
      wrap.className = 'flash';
      wrap.setAttribute('role', 'status');
      flashBox = document.createElement('div');
      flashBox.className = 'box';
      wrap.appendChild(flashBox);
      document.body.appendChild(wrap);
    }
    flashBox.innerHTML = '<b></b><span></span>';
    flashBox.firstChild.textContent = title;
    flashBox.lastChild.textContent = line;
    flashBox.parentNode.classList.add('on');
    flashBox.parentNode.classList.toggle('done', !!done);
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
    if (!delta.completed.length) {
      /* No chapter finished, but a beat did: move on to the next unfinished beat of the
         same chapter, wrapping around to an earlier one, so the reader never hunts. */
      if (!delta.beats.length) return;
      var beat = delta.beats[delta.beats.length - 1];
      var siblings = beatRecs.filter(function (r) { return r.chapter === beat.chapter; });
      var j = siblings.indexOf(beat), nextBeat = null;
      for (var m = 1; m <= siblings.length && !nextBeat; m++) {
        var s = siblings[(j + m) % siblings.length];
        if (!s.done) nextBeat = s;
      }
      if (nextBeat) nextBeat.el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    if (!delta.remaining.length) {
      flash('All chapters done', 'Tour completed', true);
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

  /* Wrap every line of a highlighted block in its own span, splitting tokens that span
     lines and reopening them on the next line, so a line can be styled on its own. Prism
     keeps every newline as text, so line N of the hunk is the Nth wrapper. Every block
     is wrapped: the first and last line paint the block's vertical padding in their own
     background, and the marks address lines by number. */
  function wrapLines(code) {
    var html = code.innerHTML, out = '<span class="ln">', open = [];
    var re = /<\/span>|<span\b[^>]*>|\n|[^<\n]+/g, tokens = [], m;
    while ((m = re.exec(html))) tokens.push(m[0]);
    for (var i = 0; i < tokens.length; i++) {
      var t = tokens[i];
      if (t === '\n') {
        /* Prism ends a run's span right after its last newline. Close those spans here,
           before the chain is reopened, or the next line would begin with an empty span
           of the previous run and be styled as part of it. */
        out += '\n';
        while (tokens[i + 1] === '</span>' && open.length) { open.pop(); out += '</span>'; i++; }
        out += open.map(function () { return '</span>'; }).join('') + '</span>';
        out += '<span class="ln">' + open.join('');
      } else if (t === '</span>') { open.pop(); out += t; }
      else if (t.charAt(0) === '<') { open.push(t); out += t; }
      else out += t;
    }
    code.innerHTML = out + '</span>';
    var last = code.lastElementChild;
    if (last && last.className === 'ln' && !last.textContent) last.remove();
  }
  function markLines(fig, code) {
    var focus = fig.getAttribute('data-focus'), dim = fig.getAttribute('data-dim');
    if (!focus && !dim) return;
    var lines = [].slice.call(code.querySelectorAll(':scope > .ln'));
    function apply(spec, cls) {
      (spec || '').split(',').forEach(function (range) {
        var parts = range.trim().split('-'), from = +parts[0], to = +(parts[1] || parts[0]);
        for (var n = from; n <= to; n++) if (lines[n - 1]) lines[n - 1].classList.add(cls);
      });
    }
    apply(dim, 'dim');
    apply(focus, 'focus');
    lines.forEach(function (ln) { if (ln.classList.contains('dim')) hoverDim(ln); });
  }

  /* Hovering a dimmed line lifts its whole run, the adjacent dimmed lines, back to full
     strength, so a reader who wants to read it after all can. The run is found from the
     siblings each time; there is no container for it. Moving between two lines of the same
     run fires a leave and an enter too, so the leave looks at where the pointer went. */
  function dimRun(ln) {
    var run = [ln], p = ln, n = ln;
    while ((p = p.previousElementSibling) && p.classList.contains('dim')) run.unshift(p);
    while ((n = n.nextElementSibling) && n.classList.contains('dim')) run.push(n);
    return run;
  }
  function hoverDim(ln) {
    ln.addEventListener('mouseenter', function () {
      dimRun(ln).forEach(function (l) { l.classList.add('lit'); });
    });
    ln.addEventListener('mouseleave', function (e) {
      var to = e.relatedTarget && e.relatedTarget.closest ? e.relatedTarget.closest('.ln.dim') : null;
      var run = dimRun(ln);
      if (to && run.indexOf(to) >= 0) return;
      run.forEach(function (l) { l.classList.remove('lit'); });
    });
  }
  /* The legend's example hunk is static, so its faded lines get their hover here. */
  [].forEach.call(document.querySelectorAll('.marks-demo .ln.dim'), hoverDim);

  function light(el) {
    if (el.classList.contains('highlighted')) return;
    el.classList.add('highlighted');
    if (window.Prism) {
      try { Prism.highlightElement(el); } catch (e) {}
    }
    wrapLines(el);
    var fig = el.closest('figure.hunk');
    if (fig) markLines(fig, el);
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

  /* ---- grow buttons: a hunk can show more of its file above and below, like on
     GitHub. The assembler embeds each changed file once, as it is at the toured tip, and
     gives every hunk its range in it (data-from, data-to). Grown lines join the hunk's
     own diff as unchanged lines, inserted as new line elements before or after the
     existing ones, so the focus and dim marks on those keep their places. A grown line
     that another hunk changed is marked, since it shows the new code as if unchanged. ---- */
  var sources = {};
  [].forEach.call(document.querySelectorAll('script[type="embedded-source-file"]'), function (tag) {
    var text = JSON.parse(tag.textContent), lines = text.split('\n');
    if (lines.length && lines[lines.length - 1] === '') lines.pop();
    /* Other hunks' changes, placed in the new file: which lines they added, and which
       removed lines stood before a given line. */
    var added = {}, removed = {};
    JSON.parse(tag.getAttribute('data-changes') || '[]').forEach(function (c) {
      if (c[1] === '+') added[c[0]] = c[3];
      else (removed[c[0]] = removed[c[0]] || []).push([c[2], c[3]]);
    });
    sources[tag.getAttribute('data-path')] = { lines: lines, added: added, removed: removed };
  });
  var STEP = 20;

  function grownLines(code, texts) {
    var pre = document.createElement('pre'), tmp = document.createElement('code');
    pre.className = code.parentNode.className;
    tmp.className = code.className.replace(/\bhighlighted\b/, '');
    tmp.textContent = texts.join('\n') + '\n';
    pre.appendChild(tmp);
    if (window.Prism) { try { Prism.highlightElement(tmp); } catch (e) {} }
    wrapLines(tmp);
    return [].slice.call(tmp.querySelectorAll(':scope > .ln'));
  }

  function grow(fig, up, all) {
    var code = fig.querySelector('pre.diff > code'), src = sources[fig.getAttribute('data-path')];
    if (!code || !src) return;
    light(code);
    var from = +fig.getAttribute('data-from'), to = +fig.getAttribute('data-to');
    var a, b;
    if (up) { b = from - 1; a = all ? 1 : Math.max(1, b - STEP + 1); }
    else { a = to + 1; b = all ? src.lines.length : Math.min(src.lines.length, a + STEP - 1); }
    if (a > b) return;
    /* Lines another hunk changed show as that hunk's diff shows them: added lines with
       a plus, removed lines put back with a minus where they stood. */
    var own = fig.id.replace(/-\d+$/, ''), texts = [], owners = [];
    function other(id) { return id && id !== own ? id : null; }
    for (var n = a; n <= b; n++) {
      (src.removed[n] || []).forEach(function (r) {
        if (other(r[1])) { texts.push('-' + r[0]); owners.push(r[1]); }
      });
      var by = other(src.added[n]);
      texts.push((by ? '+' : ' ') + src.lines[n - 1]);
      owners.push(by);
    }
    if (b === src.lines.length) (src.removed[b + 1] || []).forEach(function (r) {
      if (other(r[1])) { texts.push('-' + r[0]); owners.push(r[1]); }
    });
    var lns = grownLines(code, texts);
    lns.forEach(function (ln, i) {
      ln.classList.add('grown');
      if (!owners[i]) return;
      ln.classList.add('elsewhere');
      ln.title = 'Changed in another hunk; click to go there';
      ln.addEventListener('click', function () { location.hash = '#' + owners[i]; });
    });
    var anchor = up ? code.firstChild : null;
    lns.forEach(function (ln) { code.insertBefore(ln, anchor); });
    if (up) fig.setAttribute('data-from', a); else fig.setAttribute('data-to', b);
    paintGrow(fig);
  }

  function paintGrow(fig) {
    var src = sources[fig.getAttribute('data-path')];
    var from = +fig.getAttribute('data-from'), to = +fig.getAttribute('data-to');
    var above = from - 1, below = src.lines.length - to;
    /* A bar with nothing left to show goes away: the top one once line 1 is shown, the
       bottom one once the last line is. */
    fig.querySelector('.ctx').hidden = above <= 0;
    fig.querySelector('.grow.down').hidden = below <= 0;
    /* The header button shows the whole file, or, once the whole file is shown, returns
       the hunk to its own lines. It only disappears when the hunk is the whole file. */
    var all = fig.querySelector('figcaption button.all');
    var from0 = +fig.getAttribute('data-from0'), to0 = +fig.getAttribute('data-to0');
    all.hidden = from0 <= 1 && to0 >= src.lines.length;
    var full = above <= 0 && below <= 0;
    var label = full ? 'Show only the changed lines' : 'Show the whole file';
    all.innerHTML = icon(full ? 'fold' : 'all');
    all.title = label;
    all.setAttribute('aria-label', label);
    /* The bar names the declaration until the hunk has grown; from then on it names the
       lines it shows, which is what a reader who grew it wants to know. */
    var bar = fig.querySelector('.ctx .label');
    bar.textContent = fig.getAttribute('data-grown') ? 'Lines ' + from + '–' + to : fig.getAttribute('data-decl');
  }

  [].forEach.call(document.querySelectorAll('figure.hunk[data-path]'), function (fig) {
    var pre = fig.querySelector('pre.diff'), ctx = fig.querySelector('.ctx');
    if (!pre || !ctx || !sources[fig.getAttribute('data-path')]) return;
    function step(up, all) { fig.setAttribute('data-grown', '1'); grow(fig, up, all); }
    /* The hunk's own range and declaration, to return to. */
    fig.setAttribute('data-from0', fig.getAttribute('data-from'));
    fig.setAttribute('data-to0', fig.getAttribute('data-to'));
    fig.setAttribute('data-decl', fig.querySelector('.ctx .label').textContent);
    function shrink() {
      [].forEach.call(fig.querySelectorAll('pre.diff > code > .ln.grown'), function (ln) { ln.remove(); });
      fig.setAttribute('data-from', fig.getAttribute('data-from0'));
      fig.setAttribute('data-to', fig.getAttribute('data-to0'));
      fig.removeAttribute('data-grown');
      paintGrow(fig);
    }
    /* After a step, the bar the reader clicked stays in reach for the next one; once it
       has gone, because nothing is left in that direction, the line it reached does. */
    function keep(bar, line) {
      var target = bar.hidden ? line() : bar;
      /* Instantly: during a smooth scroll the icon would slide away from the pointer. */
      if (target) target.scrollIntoView({ block: 'nearest', behavior: 'instant' });
    }
    function lines() { return fig.querySelectorAll('pre.diff > code > .ln'); }
    ctx.insertBefore(iconButton('up', 'Show ' + STEP + ' more lines above', function () {
      step(true, false);
      keep(ctx, function () { return lines()[0]; });
    }), ctx.firstChild);
    var bar = document.createElement('div');
    bar.className = 'grow down';
    bar.appendChild(iconButton('down', 'Show ' + STEP + ' more lines below', function () {
      step(false, false);
      keep(bar, function () { var l = lines(); return l[l.length - 1]; });
    }));
    pre.parentNode.insertBefore(bar, pre.nextSibling);
    var cap = fig.querySelector('figcaption'), where = cap && cap.querySelector('.where');
    if (where) where.parentNode.insertBefore(iconButton('all', 'Show the whole file', function () {
      var src = sources[fig.getAttribute('data-path')];
      if (+fig.getAttribute('data-from') <= 1 && +fig.getAttribute('data-to') >= src.lines.length) { shrink(); return; }
      collapse(fig, false); step(true, true); step(false, true);
    }), where.nextSibling);
    paintGrow(fig);
  });

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
