/* Daniance: the Ask card on Home, played from the real Figma frames.
   It loops on its own while it is on screen. Pressing the question opens
   it, anything outside the card (or Escape) folds it back, and the button
   pauses or restarts the loop. With reduced motion it never plays itself. */
(function () {
  var root = document.querySelector('[data-dx]');
  if (!root) return;
  var stage = root.querySelector('.dx__stage');
  var ask = root.querySelector('.dx__ask');
  var hit = root.querySelector('.dx__hit');
  var cursor = root.querySelector('.dx__cursor');
  var steps = root.querySelectorAll('.dx__steps li');
  var btn = root.querySelector('.dx__play');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var timers = [], playing = false, visible = false, userTook = false, answerTimer = null;
  var P = { rest: [83.3, 91], chip: [28.9, 50.9], out: [62.5, 15.6] };

  function state(s) { root.setAttribute('data-state', s); }
  function step(i) { steps.forEach(function (li, k) { li.classList.toggle('is-on', k === i); }); }
  function move(p) { cursor.style.left = p[0] + '%'; cursor.style.top = p[1] + '%'; }
  function click() {
    cursor.classList.remove('is-click'); void cursor.offsetWidth; cursor.classList.add('is-click');
  }
  function clear() { timers.forEach(clearTimeout); timers = []; }
  function at(ms, fn) { timers.push(setTimeout(fn, ms)); }

  function loop() {
    clear();
    move(P.rest); state('home'); step(0);
    at(700, function () { move(P.chip); });
    at(1700, click);
    at(1850, function () { state('thinking'); step(1); });
    at(3300, function () { state('answer'); });
    at(6200, function () { move(P.out); step(2); });
    at(7200, click);
    at(7350, function () { state('home'); });
    at(9400, loop);
  }
  function play() {
    if (playing) return;
    playing = true; root.classList.add('is-playing'); btn.textContent = 'Pause'; loop();
  }
  function stop(label) {
    playing = false; clear(); root.classList.remove('is-playing');
    btn.textContent = label || 'Play';
  }

  // a visitor can drive it
  function open() {
    stop('Play on its own'); userTook = true;
    clearTimeout(answerTimer);
    state('thinking'); step(1);
    answerTimer = setTimeout(function () { state('answer'); }, reduce ? 0 : 1300);
  }
  function close() {
    clearTimeout(answerTimer);
    state('home'); step(2);
  }
  hit.addEventListener('click', function (e) { e.stopPropagation(); open(); });
  stage.addEventListener('click', function (e) {
    var s = root.getAttribute('data-state');
    if (s !== 'home' && !ask.contains(e.target)) { stop('Play on its own'); userTook = true; close(); }
  });
  root.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && root.getAttribute('data-state') !== 'home') { close(); hit.focus(); }
  });
  btn.addEventListener('click', function () {
    if (playing) { stop('Play'); userTook = true; }
    else { userTook = false; play(); }
  });

  // only plays while it can be seen, and never by itself under reduced motion
  if (reduce) { btn.textContent = 'Play'; step(0); return; }
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        visible = en.isIntersecting;
        if (visible && !userTook) play();
        else if (!visible && playing) stop('Play');
      });
    }, { threshold: 0.4 }).observe(stage);
  } else { play(); }
})();
