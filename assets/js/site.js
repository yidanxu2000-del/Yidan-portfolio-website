(function(){
  var nav = document.querySelector('.navbar');
  if(nav){
    var lastScrollY = window.scrollY;
    var onScroll = function(){
      var y = window.scrollY;
      if(y > 24) nav.classList.add('is-scrolled');
      else nav.classList.remove('is-scrolled');

      // hide the bar while scrolling down past the first screen, reveal it
      // again as soon as the user scrolls back up
      if(y > lastScrollY + 4 && y > 120){
        nav.classList.add('is-hidden');
      } else if(y < lastScrollY - 4 || y <= 120){
        nav.classList.remove('is-hidden');
      }
      lastScrollY = y;
    };
    window.addEventListener('scroll', onScroll, {passive:true});
    onScroll();

    var toggle = nav.querySelector('.navbar__toggle');
    var mobile = nav.querySelector('.navbar__mobile');
    if(toggle && mobile){
      toggle.addEventListener('click', function(){
        var open = mobile.classList.toggle('is-open');
        toggle.textContent = open ? '✕' : '☰';
      });
      mobile.querySelectorAll('a').forEach(function(a){
        a.addEventListener('click', function(){
          mobile.classList.remove('is-open');
          toggle.textContent = '☰';
        });
      });
    }
  }

  // ---- filterable illustration gallery + lightbox ----------------------
  // The grid is the source of truth: the lightbox reads whatever is
  // currently visible, so arrow keys walk the filtered set rather than
  // jumping to a picture the viewer has just filtered away.
  (function(){
    var grid = document.querySelector('.gal-grid');
    var box = document.querySelector('.lightbox');
    if(!grid || !box) return;
    var items = [].slice.call(grid.querySelectorAll('.gal-item'));
    var chips = [].slice.call(document.querySelectorAll('.gal-chip'));
    var img = box.querySelector('img');
    var cap = box.querySelector('.lightbox__cap');
    var count = box.querySelector('.lightbox__count');
    var idx = 0, lastFocus = null;

    function visible(){ return items.filter(function(el){ return !el.classList.contains('is-hidden'); }); }

    chips.forEach(function(chip){
      chip.addEventListener('click', function(){
        var f = chip.dataset.filter;
        chips.forEach(function(c){ c.setAttribute('aria-pressed', String(c === chip)); });
        items.forEach(function(el){
          el.classList.toggle('is-hidden', f !== 'all' && el.dataset.cat !== f);
        });
      });
    });

    function show(i){
      var list = visible();
      if(!list.length) return;
      idx = (i + list.length) % list.length;
      var el = list[idx];
      var full = el.dataset.full || el.querySelector('img').src;
      img.src = full;
      img.alt = el.querySelector('img').alt;
      cap.innerHTML = '<b>' + el.dataset.title + '</b>' + (el.dataset.note || '');
      count.textContent = (idx + 1) + ' / ' + list.length;
    }
    function open(el){
      lastFocus = document.activeElement;
      show(visible().indexOf(el));
      box.classList.add('is-open');
      document.body.style.overflow = 'hidden';
      box.querySelector('.lightbox__close').focus();
    }
    function close(){
      box.classList.remove('is-open');
      document.body.style.overflow = '';
      img.removeAttribute('src');
      if(lastFocus) lastFocus.focus();
    }
    items.forEach(function(el){ el.addEventListener('click', function(){ open(el); }); });
    box.querySelector('.lightbox__close').addEventListener('click', close);
    box.querySelector('.lightbox__btn--prev').addEventListener('click', function(){ show(idx - 1); });
    box.querySelector('.lightbox__btn--next').addEventListener('click', function(){ show(idx + 1); });
    box.addEventListener('click', function(e){ if(e.target === box) close(); });
    document.addEventListener('keydown', function(e){
      if(!box.classList.contains('is-open')) return;
      if(e.key === 'Escape') close();
      else if(e.key === 'ArrowLeft') show(idx - 1);
      else if(e.key === 'ArrowRight') show(idx + 1);
    });
  })();

  // ---- dice ------------------------------------------------------------
  // The die is a real 3D cube. Opposite faces sum to seven: 1 front, 6 back,
  // 3 right, 4 left, 5 top, 2 bottom. To show a face, turn the cube so that
  // face ends up pointing at the viewer.
  var FACE_TURN = {
    1: [0, 0],      // front, already facing us
    6: [0, 180],    // back
    3: [0, -90],    // right
    4: [0, 90],     // left
    5: [90, 0],     // top
    2: [-90, 0]     // bottom
  };

  var ROLL_MS = 2600;

  // Every roll adds whole turns on top of the last resting angle, so the die
  // always spins forward. Reusing absolute angles would make it unwind.
  function rollDie(die, face, spins){
    var turn = FACE_TURN[face] || FACE_TURN[1];
    var laps = die._laps || 0;
    laps += (spins || 4);
    die._laps = laps;
    var x = turn[0] + 360 * laps;
    var y = turn[1] + 360 * laps;
    die.classList.add('is-controlled');
    die.classList.remove('is-snapping');
    void die.offsetWidth;
    die.style.transform = 'rotateX(' + x + 'deg) rotateY(' + y + 'deg)';
  }

  // hero: the die lands, then the words arrive. After that every click rolls
  // a new face, and the line under the die changes to match it.
  (function(){
    var hero = document.querySelector('.hero-dice');
    if(!hero) return;
    var die = hero.querySelector('.die');
    var word = hero.querySelector('.hero-dice__roll');
    var faces = [];
    [].forEach.call(hero.querySelectorAll('.hero-dice__words li'), function(li){
      faces[+li.dataset.n] = li.textContent;
    });
    if(reduceMotion){
      hero.classList.remove('is-intro');
      hero.classList.add('is-lit');
    } else {
      setTimeout(function(){ hero.classList.add('is-lit'); }, 850);
      setTimeout(function(){ hero.classList.remove('is-intro'); }, 1500);
    }
    if(!die) return;
    var last = 1, busy = false;
    die.addEventListener('click', function(){
      if(busy) return;
      busy = true;
      var face = 1 + Math.floor(Math.random() * 6);
      if(face === last) face = (face % 6) + 1;   // always a visible change
      last = face;
      rollDie(die, face, 4);
      if(word && faces[face]){
        word.classList.add('is-swapping');
        setTimeout(function(){
          word.textContent = faces[face];
          word.classList.remove('is-swapping');
        }, ROLL_MS * 0.62);
      }
      setTimeout(function(){ busy = false; }, ROLL_MS);
    });
  })();

  // picker: roll, show what came up, then go there
  (function(){
    var picker = document.querySelector('.dice-picker');
    if(!picker) return;
    var die = picker.querySelector('.die');
    var result = picker.querySelector('.dice-result');
    var elNum = picker.querySelector('.dice-result__num');
    var elName = picker.querySelector('.dice-result__name');
    var elDesc = picker.querySelector('.dice-result__desc');
    var elGo = picker.querySelector('.dice-result__go');
    var again = picker.querySelector('.dice-result__again');
    var map = {};
    [].forEach.call(picker.querySelectorAll('.dice-map li'), function(li){
      map[li.dataset.n] = li.dataset;
    });
    var rolling = false;

    function roll(){
      if(rolling) return;
      rolling = true;
      result.classList.remove('is-shown');
      result.hidden = true;
      var face = 1 + Math.floor(Math.random() * 6);
      var item = map[face];
      if(!item){ rolling = false; return; }
      rollDie(die, face, reduceMotion ? 0 : 5);
      setTimeout(function(){
        elNum.textContent = 'Project ' + face;
        elName.textContent = item.name;
        elDesc.textContent = item.desc;
        elGo.setAttribute('href', item.href);
        elGo.textContent = 'Open ' + item.name;
        result.hidden = false;
        void result.offsetWidth;
        result.classList.add('is-shown');
        rolling = false;
        // No automatic jump. Most people want to roll again, and being thrown
        // into a project takes that choice away.
      }, reduceMotion ? 60 : ROLL_MS);
    }

    // clicking the die is always 'throw it again', even while a result sits
    // on screen
    die.addEventListener('click', roll);
    if(again) again.addEventListener('click', roll);
  })();

  // swatches fill in when they reach the viewport
  (function(){
    var chips = document.querySelectorAll('.swatch');
    if(!chips.length) return;
    if(!('IntersectionObserver' in window)){
      [].forEach.call(chips, function(c){ c.classList.add('is-in'); });
      return;
    }
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if(e.isIntersecting){ e.target.classList.add('is-in'); io.unobserve(e.target); }
      });
    }, {threshold:.35});
    [].forEach.call(chips, function(c){ io.observe(c); });
  })();

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // true only on devices that actually have a mouse/trackpad — touch fires a
  // single synthetic mousemove at the tap point after tap-and-release, which
  // would otherwise trigger the cursor-proximity glow/tooltip meant for a
  // continuously-moving pointer, ballooning up several nearby stars at once
  // on a screen where a 240px glow radius covers half the width
  var hasHover = !window.matchMedia || window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  // shared twinkling star-canvas renderer, reused by the interactive
  // starfield and the ambient (decorative) hero version
  function paintTwinklingStars(canvas, host, opts){
    if(!canvas || reduceMotion) return null;
    opts = opts || {};
    var ctx = canvas.getContext('2d');
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = 0, h = 0, bgStars = [];
    var mouse = {x:-9999,y:-9999};
    var parallax = {nx:0, ny:0};
    var parallaxTarget = {nx:0, ny:0};
    var entranceMs = opts.entrance ? 1500 : 0;
    var startTime = opts.entranceManual ? null : performance.now();

    function resize(){
      w = host.clientWidth; h = host.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
      ctx.setTransform(dpr,0,0,dpr,0,0);
      var count = Math.round((w * h) / (opts.density || 9000));
      bgStars = [];
      // a handful of stars pick up a faint nebula tint (pale blue / violet / gold)
      // so the field reads as colourful star-cloud, not flat white dots
      var tints = ['255,255,255', '186,196,255', '170,210,255', '255,224,178'];
      for(var i=0;i<count;i++){
        var tint = Math.random() < 0.72 ? tints[0] : tints[1 + Math.floor(Math.random()*3)];
        var r = Math.random()*1.2 + 0.3;
        bgStars.push({
          x: Math.random()*w, y: Math.random()*h,
          r: r,
          phase: Math.random()*Math.PI*2,
          speed: 0.5 + Math.random()*1.2,
          tint: tint,
          depth: (r - 0.3) / 1.2
        });
      }
      // a small set of larger, closer "foreground" stars that drift further
      // with the cursor than the background field, so the scene reads as
      // layered space rather than one flat plane
      if(opts.foreground){
        var fgCount = Math.max(10, Math.round((w * h) / 90000));
        for(var j=0;j<fgCount;j++){
          bgStars.push({
            x: Math.random()*w, y: Math.random()*h,
            r: Math.random()*1.6 + 1.6,
            phase: Math.random()*Math.PI*2,
            speed: 0.4 + Math.random()*0.8,
            tint: Math.random() < 0.6 ? tints[0] : tints[1 + Math.floor(Math.random()*3)],
            depth: 1.4 + Math.random()*0.6
          });
        }
      }
    }

    var t = 0;
    function draw(){
      t += 0.016;
      ctx.clearRect(0,0,w,h);
      if(opts.glow && mouse.x > -999){
        var g = ctx.createRadialGradient(mouse.x,mouse.y,0,mouse.x,mouse.y,260);
        g.addColorStop(0,'rgba(70,150,230,0.18)');
        g.addColorStop(1,'rgba(70,150,230,0)');
        ctx.fillStyle = g;
        ctx.fillRect(0,0,w,h);
      }
      var ep = entranceMs ? (startTime === null ? 0 : Math.min(1, (performance.now() - startTime) / entranceMs)) : 1;
      var eased = 1 - Math.pow(1 - ep, 3);
      var cx = w / 2, cy = h / 2;
      parallax.nx += (parallaxTarget.nx - parallax.nx) * 0.06;
      parallax.ny += (parallaxTarget.ny - parallax.ny) * 0.06;
      for(var i=0;i<bgStars.length;i++){
        var s = bgStars[i];
        var tw = 0.55 + 0.45*Math.sin(t*s.speed + s.phase);
        var alpha = 0.25 + 0.55*tw;
        // per-star depth parallax: nearer (larger) stars drift further with
        // the cursor than distant ones, so the field has real spatial layers
        var px = s.x + parallax.nx * s.depth * 22;
        var py = s.y + parallax.ny * s.depth * 16;
        if(ep < 1){
          // warp-in: stars streak outward from centre into their resting
          // position, like arriving at light-speed into the field
          var fx = cx + (px - cx) * eased;
          var fy = cy + (py - cy) * eased;
          var trail = (1 - eased) * 0.55;
          ctx.beginPath();
          ctx.moveTo(fx - (px - cx) * trail, fy - (py - cy) * trail);
          ctx.lineTo(fx, fy);
          ctx.strokeStyle = 'rgba(' + s.tint + ',' + (alpha * ep).toFixed(3) + ')';
          ctx.lineWidth = Math.max(0.3, s.r * 0.9);
          ctx.stroke();
        } else {
          ctx.beginPath();
          ctx.arc(px, py, s.r, 0, Math.PI*2);
          ctx.fillStyle = 'rgba(' + s.tint + ',' + alpha + ')';
          ctx.fill();
        }
      }
      requestAnimationFrame(draw);
    }

    resize();
    requestAnimationFrame(draw);
    window.addEventListener('resize', resize);
    return {
      setMouse: function(x,y){ mouse.x = x; mouse.y = y; },
      setParallax: function(nx,ny){ parallaxTarget.nx = nx; parallaxTarget.ny = ny; },
      triggerEntrance: function(){ if(startTime === null) startTime = performance.now(); }
    };
  }

  // ambient hero starfield — twinkling stars, plus a subtle mouse-driven
  // 3D tilt so the scene feels like it has real depth, not a flat backdrop
  var heroField = document.querySelector('.hero-starfield');
  if(heroField){
    var heroCanvas = heroField.querySelector('canvas');
    var heroRenderer = paintTwinklingStars(heroCanvas, heroField, {density:11000, glow:false, entrance:true, foreground:true});

    var heroSection = heroField.closest('.section--full') || heroField.parentElement;
    if(heroSection && !reduceMotion){
      heroSection.addEventListener('mousemove', function(e){
        var rect = heroSection.getBoundingClientRect();
        var nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;   // -1 .. 1
        var ny = ((e.clientY - rect.top) / rect.height) * 2 - 1;
        heroCanvas.style.transform = 'rotateX(' + (-ny*5).toFixed(2) + 'deg) rotateY(' + (nx*7).toFixed(2) + 'deg) scale(1.05) translate(' + (-nx*14).toFixed(1) + 'px,' + (-ny*10).toFixed(1) + 'px)';
        if(heroRenderer) heroRenderer.setParallax(nx, ny);
      });
      heroSection.addEventListener('mouseleave', function(){
        heroCanvas.style.transform = 'rotateX(0deg) rotateY(0deg) scale(1) translate(0,0)';
        if(heroRenderer) heroRenderer.setParallax(0, 0);
      });
    }
  }

  // interactive project starfield
  var field = document.querySelector('.starfield-section');
  if(field){
    var canvas = field.querySelector('.starfield-canvas');
    var linksLayer = field.querySelector('.starfield-links');
    var mouse = {x:-9999,y:-9999};
    var isDragging = false;
    var renderer = paintTwinklingStars(canvas, field, {density:9000, glow:true, entrance:true, entranceManual:true, foreground:true});

    // entrance: the moment this section scrolls into view, the whole field
    // swirls/rotates into place (canvas stars warp in, the star-links layer
    // spins down from an angle) instead of just sitting there static —
    // works identically on touch, no mouse needed, so mobile gets it too
    var stars = linksLayer ? Array.prototype.slice.call(linksLayer.querySelectorAll('.star-link')) : [];
    if('IntersectionObserver' in window){
      var burstIO = new IntersectionObserver(function(entries){
        entries.forEach(function(entry){
          if(entry.isIntersecting){
            if(renderer) renderer.triggerEntrance();
            field.classList.add('is-revealed');
            canvas.classList.add('is-revealing');
            if(linksLayer) linksLayer.classList.add('is-revealing');
            // one-shot animation only — drop the class once it's done so it
            // never lingers and fights the mouse-driven inline transform
            setTimeout(function(){
              canvas.classList.remove('is-revealing');
              if(linksLayer) linksLayer.classList.remove('is-revealing');
            }, 1750);
            stars.forEach(function(star, i){
              setTimeout(function(){ star.classList.add('is-burst'); }, 40 * i);
            });
            burstIO.disconnect();
          }
        });
      }, {threshold:0.15});
      burstIO.observe(field);
    } else {
      if(renderer) renderer.triggerEntrance();
      field.classList.add('is-revealed');
      stars.forEach(function(star){ star.classList.add('is-burst'); });
    }

    if(hasHover){
      field.addEventListener('mousemove', function(e){
        var rect = field.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
        if(renderer) renderer.setMouse(mouse.x, mouse.y);
        updateStarIntensity();

        if(!reduceMotion){
          var nx = (mouse.x / rect.width) * 2 - 1;   // -1 .. 1
          var ny = (mouse.y / rect.height) * 2 - 1;
          if(renderer) renderer.setParallax(nx, ny);
          // dragging (mouse held down) reads as actually grabbing and
          // spinning the field like a 3D model — bigger rotation, a
          // perspective push toward the viewer — rather than the
          // subtler drift it does on a passive hover-by
          var rotY = nx * (isDragging ? 20 : 6);
          var rotX = -ny * (isDragging ? 13 : 4);
          var pushZ = isDragging ? 40 : 0;
          linksLayer.style.transform = 'translateZ(' + pushZ + 'px) rotateX(' + rotX + 'deg) rotateY(' + rotY + 'deg)';
          canvas.style.transform = 'translate(' + (-nx*8) + 'px,' + (-ny*8) + 'px) scale(' + (isDragging ? 1.06 : 1.03) + ')';
        }
      });
      field.addEventListener('mouseleave', function(){
        mouse.x = -9999; mouse.y = -9999;
        isDragging = false;
        field.classList.remove('is-pressed');
        if(renderer){ renderer.setMouse(mouse.x, mouse.y); renderer.setParallax(0, 0); }
        updateStarIntensity();
        linksLayer.style.transform = 'rotateX(0deg) rotateY(0deg)';
        canvas.style.transform = 'translate(0,0) scale(1)';
      });
    }

    var clickableStars = linksLayer ? Array.prototype.slice.call(linksLayer.querySelectorAll('.star-link:not(.star-link--disabled)')) : [];
    var tooltip = field.querySelector('.star-tooltip');
    var tooltipTitle = tooltip && tooltip.querySelector('.star-tooltip__title');
    var tooltipMeta = tooltip && tooltip.querySelector('.star-tooltip__meta');
    var tooltipDesc = tooltip && tooltip.querySelector('.star-tooltip__desc');
    var activeStar = null;
    var ticking = false;
    function updateStarIntensity(){
      if(ticking) return;
      ticking = true;
      requestAnimationFrame(function(){
        var rect = field.getBoundingClientRect();
        var nearest = null, nearestDist = Infinity;
        clickableStars.forEach(function(star){
          var r = star.getBoundingClientRect();
          var cx = r.left + r.width/2 - rect.left;
          var cy = r.top + r.height/2 - rect.top;
          var dist = Math.hypot(mouse.x - cx, mouse.y - cy);
          var intensity = Math.max(0, 1 - dist/240);
          var dot = star.querySelector('.star-link__dot');
          var label = star.querySelector('.star-link__label');
          if(dot){
            var scale = 1 + intensity*1.6;
            dot.style.transform = 'scale(' + scale + ')';
            dot.style.boxShadow = '0 0 ' + (6+intensity*24) + 'px ' + (1+intensity*6) + 'px rgba(160,200,255,' + (0.55+intensity*0.4) + ')';
          }
          if(label){
            label.style.opacity = String(Math.min(1, 0.5 + intensity*1.4));
          }
          if(dist < nearestDist){ nearestDist = dist; nearest = star; }
        });

        if(tooltip){
          if(nearest && nearestDist < 130){
            if(activeStar !== nearest){
              activeStar = nearest;
              if(tooltipTitle) tooltipTitle.textContent = nearest.dataset.title || nearest.querySelector('.star-link__label').textContent;
              if(tooltipMeta) tooltipMeta.textContent = nearest.dataset.meta || '';
              if(tooltipDesc) tooltipDesc.textContent = nearest.dataset.desc || '';
            }
            var flip = mouse.x > rect.width - 260;
            tooltip.style.left = mouse.x + 'px';
            tooltip.style.top = mouse.y + 'px';
            tooltip.style.transform = flip
              ? 'translate(calc(-100% - 18px),-50%) scale(1)'
              : 'translate(18px,-50%) scale(1)';
            tooltip.classList.add('is-shown');
          } else {
            activeStar = null;
            tooltip.classList.remove('is-shown');
          }
        }
        ticking = false;
      });
    }

    // pressed cursor state, and dragging state for the model-like spin
    field.addEventListener('mousedown', function(){ field.classList.add('is-pressed'); isDragging = true; });
    field.addEventListener('mouseup', function(){ field.classList.remove('is-pressed'); isDragging = false; });
    field.addEventListener('mouseleave', function(){ field.classList.remove('is-pressed'); isDragging = false; });

    // smooth warp-out transition before navigating to a project
    clickableStars.forEach(function(star){
      star.addEventListener('click', function(e){
        if(reduceMotion) return; // instant nav, no transition
        var href = star.getAttribute('href');
        if(!href) return;
        e.preventDefault();
        stars.forEach(function(s){ s.classList.add('is-navigating'); });
        linksLayer.classList.add('is-navigating');
        canvas.classList.add('is-navigating');
        setTimeout(function(){ window.location.href = href; }, 380);
      });
    });
  }

  var glassEls = document.querySelectorAll('.liquid-glass');
  if(glassEls.length && !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    glassEls.forEach(function(el){
      el.addEventListener('pointermove', function(e){
        var r = el.getBoundingClientRect();
        if(!r.width || !r.height) return;
        var mx = ((e.clientX - r.left) / r.width) * 100;
        var my = ((e.clientY - r.top) / r.height) * 100;
        el.style.setProperty('--mx', mx.toFixed(1) + '%');
        el.style.setProperty('--my', my.toFixed(1) + '%');
      });
      el.addEventListener('pointerleave', function(){
        el.style.removeProperty('--mx');
        el.style.removeProperty('--my');
      });
    });
  }

  var starfieldSections = document.querySelectorAll('.starfield-section, .hero-starfield');
  if(starfieldSections.length && !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    starfieldSections.forEach(function(field){
      field.addEventListener('mousemove', function(e){
        var r = field.getBoundingClientRect();
        var px = ((e.clientX - r.left) / r.width - 0.5) * 2;
        var py = ((e.clientY - r.top) / r.height - 0.5) * 2;
        field.style.setProperty('--parallax-x', (px * 14).toFixed(1) + 'px');
        field.style.setProperty('--parallax-y', (py * 10).toFixed(1) + 'px');
      });
      field.addEventListener('mouseleave', function(){
        field.style.setProperty('--parallax-x', '0px');
        field.style.setProperty('--parallax-y', '0px');
      });
    });
  }

  // Swap a video facade for the real player only once it's asked for, so
  // nothing is requested from YouTube on page load and a blocked embed can
  // never render as a bare black rectangle.
  document.querySelectorAll('.video-embed--facade').forEach(function(wrap){
    var facade = wrap.querySelector('.video-facade');
    if(!facade) return;
    facade.addEventListener('click', function(){
      var id = wrap.getAttribute('data-video');
      if(!id) return;
      var frame = document.createElement('iframe');
      frame.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0';
      frame.title = facade.querySelector('.video-facade__label').textContent;
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
      frame.setAttribute('allowfullscreen', '');
      wrap.replaceChild(frame, facade);
    });
  });

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- numbers count up when they first scroll into view ----------------
  // Values are written by hand in the markup and come in a lot of shapes
  // ("5", "1.3K+", "82%+", "2 wks", "2x"), so animate whatever leading
  // number is there and leave any prefix/suffix untouched.
  (function(){
    var nodes = document.querySelectorAll('.stat__value, .prose-stat-callout__value');
    if(!nodes.length || !('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(!entry.isIntersecting) return;
        var el = entry.target;
        io.unobserve(el);
        var m = /^(\D*?)(\d+(?:\.\d+)?)(.*)$/.exec(el.textContent.trim());
        if(!m) return;
        var pre = m[1], target = parseFloat(m[2]), post = m[3];
        if(reduceMotion || !isFinite(target)) return;
        var decimals = (m[2].split('.')[1] || '').length;
        var dur = 900, start = 0;
        var step = function(ts){
          if(!start) start = ts;
          var p = Math.min(1, (ts - start) / dur);
          var eased = 1 - Math.pow(1 - p, 3);
          el.textContent = pre + (target * eased).toFixed(decimals) + post;
          if(p < 1) requestAnimationFrame(step);
          else el.textContent = pre + m[2] + post;
        };
        el.textContent = pre + (0).toFixed(decimals) + post;
        requestAnimationFrame(step);
      });
    }, {threshold:.4});
    nodes.forEach(function(el){ io.observe(el); });
  })();

  // ---- scroll progress bar + section rail -------------------------------
  (function(){
    var bar = document.createElement('div');
    bar.className = 'scroll-progress';
    document.body.appendChild(bar);
    var onProgress = function(){
      var max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.transform = 'scaleX(' + (max > 0 ? window.scrollY / max : 0) + ')';
    };
    window.addEventListener('scroll', onProgress, {passive:true});
    window.addEventListener('resize', onProgress);
    onProgress();

    // Only worth a rail on the long reads: the case studies, which are the
    // pages built out of stacked .prose-section blocks.
    var heads = Array.prototype.filter.call(
      document.querySelectorAll('.prose-section h2, .section--tint .section__title'),
      function(h){ return h.textContent.trim().length; }
    );
    if(heads.length < 3) return;

    var rail = document.createElement('nav');
    rail.className = 'section-rail';
    rail.setAttribute('aria-label', 'Sections');
    var items = heads.map(function(h, i){
      if(!h.id) h.id = 'sec-' + (i + 1);
      var a = document.createElement('a');
      a.className = 'section-rail__item';
      a.href = '#' + h.id;
      a.innerHTML = '<span class="section-rail__tick"></span><span class="section-rail__label"></span>';
      a.querySelector('.section-rail__label').textContent = h.textContent.trim();
      rail.appendChild(a);
      return a;
    });
    document.body.appendChild(rail);

    var syncActive = function(){
      var best = 0, bestTop = -Infinity;
      heads.forEach(function(h, i){
        var top = h.getBoundingClientRect().top - 120;
        if(top <= 0 && top > bestTop){ bestTop = top; best = i; }
      });
      items.forEach(function(a, i){ a.classList.toggle('is-active', i === best); });
    };
    window.addEventListener('scroll', syncActive, {passive:true});
    syncActive();
  })();

  // ---- hero rotating line -----------------------------------------------
  (function(){
    var word = document.querySelector('.hero-rotator__word');
    if(!word) return;
    var words = (word.getAttribute('data-words') || '').split('|').filter(Boolean);
    if(words.length < 2) return;
    if(reduceMotion) return; // leave the first word in place
    var wi = 0, ci = words[0].length, deleting = true;
    var tick = function(){
      var full = words[wi];
      ci += deleting ? -1 : 1;
      word.textContent = full.slice(0, ci);
      var delay = deleting ? 40 : 70;
      if(!deleting && ci === full.length){ deleting = true; delay = 1900; }
      else if(deleting && ci === 0){ deleting = false; wi = (wi + 1) % words.length; delay = 260; }
      setTimeout(tick, delay);
    };
    setTimeout(tick, 2200);
  })();

  // ---- cursor-follow glow on dark sections ------------------------------
  if(hasHover && !reduceMotion){
    document.querySelectorAll('.glow-follow').forEach(function(el){
      el.addEventListener('mousemove', function(e){
        var r = el.getBoundingClientRect();
        el.style.setProperty('--gx', ((e.clientX - r.left) / r.width * 100) + '%');
        el.style.setProperty('--gy', ((e.clientY - r.top) / r.height * 100) + '%');
        el.classList.add('is-glowing');
      });
      el.addEventListener('mouseleave', function(){ el.classList.remove('is-glowing'); });
    });
  }

  var reveals = document.querySelectorAll('.reveal');
  if('IntersectionObserver' in window && reveals.length){
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(entry.isIntersecting){
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, {threshold:0, rootMargin:'0px 0px -10% 0px'});
    reveals.forEach(function(el){ io.observe(el); });
  } else {
    reveals.forEach(function(el){ el.classList.add('is-visible'); });
  }
})();

/* ---------- Scroll-scrubbed palette morph ----------
   Reads the whole change out of the markup (each bar carries its own from/to
   colour and the slice of scroll it animates across), so the story lives in
   the HTML and this stays a generic driver. */
(function(){
  var sections = document.querySelectorAll('.palette-morph');
  if(!sections.length) return;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function hex2rgb(h){
    h = (h || '').replace('#','');
    if(h.length === 3) h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
    var n = parseInt(h, 16);
    return isNaN(n) ? null : [(n>>16)&255, (n>>8)&255, n&255];
  }
  function rgb2hex(c){
    return '#' + c.map(function(v){
      return ('0' + Math.round(v).toString(16)).slice(-2);
    }).join('').toUpperCase();
  }
  function clamp(v){ return v < 0 ? 0 : v > 1 ? 1 : v; }
  // ease so each bar settles rather than stopping dead at the end of its slice
  function ease(t){ return t < .5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; }

  sections.forEach(function(sec){
    var bars = [].slice.call(sec.querySelectorAll('.pmorph'));
    var caps = [].slice.call(sec.querySelectorAll('.palette-morph__caption span'));
    var railFill = sec.querySelector('.palette-morph__rail i');
    var swapLabel = sec.querySelector('.pgroup--swap .pgroup__label');

    bars.forEach(function(b){
      b._sw = b.querySelector('.pmorph__swatch');
      b._hex = b.querySelector('.pmorph__hex');
      b._role = b.querySelector('.pmorph__role');
      b._from = hex2rgb(b.dataset.from);
      b._to = hex2rgb(b.dataset.to);
      b._start = parseFloat(b.dataset.start);
      b._end = parseFloat(b.dataset.end);
      b._mode = b.dataset.mode || 'shift';
      b._mid = parseFloat(b.dataset.mid);
      b._mid2 = parseFloat(b.dataset.mid2);
      b._roleTo = b.dataset.roleTo || '';
      b._roleFrom = b._role ? b._role.textContent : '';
    });

    function paint(p){
      bars.forEach(function(b){
        if(!b._sw) return;
        var span = b._end - b._start;
        var t = ease(clamp(span > 0 ? (p - b._start) / span : (p >= b._end ? 1 : 0)));

        if(b._mode === 'swap'){
          // One column carries the whole argument: the dead colour drains out
          // of the system, the slot sits empty, then the accent rises into the
          // space it left. Same column throughout, so nothing shifts sideways.
          var out = ease(clamp((p - b._start) / (b._mid - b._start)));
          var back = ease(clamp((p - b._mid2) / (b._end - b._mid2)));
          var empty = out >= 1 && back <= 0;
          if(back > 0){
            b._sw.style.backgroundColor = rgb2hex(b._to);
            b._sw.style.height = (100 * back) + '%';
            b._sw.style.opacity = '1';
            b._sw.style.boxShadow = '0 0 ' + (34 * back).toFixed(1) + 'px ' +
              (5 * back).toFixed(1) + 'px rgba(102,205,219,' + (.5 * back).toFixed(2) + ')';
          } else {
            b._sw.style.backgroundColor = rgb2hex(b._from);
            b._sw.style.height = (100 * (1 - out)) + '%';
            b._sw.style.opacity = String(1 - out);
            b._sw.style.boxShadow = 'none';
          }
          b.classList.toggle('pmorph--gone', empty);
          sec.classList.toggle('is-accent-in', back > 0);
          if(swapLabel){
            swapLabel.textContent = back > 0 ? 'New accent added'
              : (out > .6 ? 'Removed from the system' : 'One dead colour');
            swapLabel.classList.toggle('is-accent', back > 0);
          }
          if(b._role) b._role.textContent = back > 0 ? b._roleTo : b._roleFrom;
          if(b._hex) b._hex.textContent = back > 0 ? rgb2hex(b._to)
            : (out > .6 ? 'removed' : rgb2hex(b._from));
          return;
        }

        // the ordinary case: one colour interpolating into another
        var cur = [0,1,2].map(function(i){ return b._from[i] + (b._to[i] - b._from[i]) * t; });
        b._sw.style.backgroundColor = rgb2hex(cur);
        b._sw.style.height = '100%';
        if(b._hex) b._hex.textContent = rgb2hex(cur);
      });

      var step = 0;
      for(var i = 0; i < caps.length; i++){
        if(p >= parseFloat(caps[i].dataset.at || 0)) step = i;
      }
      caps.forEach(function(c, i){ c.classList.toggle('is-on', i === step); });
      if(railFill) railFill.style.width = (p * 100).toFixed(2) + '%';
    }

    if(reduceMotion){ paint(1); return; }

    var ticking = false;
    function frame(){
      ticking = false;
      var track = sec.querySelector('.palette-morph__track') || sec;
      var r = track.getBoundingClientRect();
      var total = track.offsetHeight - window.innerHeight;
      paint(total > 0 ? clamp(-r.top / total) : 0);
    }
    function onScroll(){
      if(ticking) return;
      ticking = true;
      window.requestAnimationFrame(frame);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    frame();
  });
})();
