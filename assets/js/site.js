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

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
    var renderer = paintTwinklingStars(canvas, field, {density:9000, glow:true, entrance:true, entranceManual:true});

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
            }, 1450);
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

    field.addEventListener('mousemove', function(e){
      var rect = field.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
      if(renderer) renderer.setMouse(mouse.x, mouse.y);
      updateStarIntensity();

      if(!reduceMotion){
        var nx = (mouse.x / rect.width) * 2 - 1;   // -1 .. 1
        var ny = (mouse.y / rect.height) * 2 - 1;
        var rotY = nx * 6;   // deg
        var rotX = -ny * 4;  // deg
        linksLayer.style.transform = 'rotateX(' + rotX + 'deg) rotateY(' + rotY + 'deg)';
        canvas.style.transform = 'translate(' + (-nx*8) + 'px,' + (-ny*8) + 'px) scale(1.03)';
      }
    });
    field.addEventListener('mouseleave', function(){
      mouse.x = -9999; mouse.y = -9999;
      if(renderer) renderer.setMouse(mouse.x, mouse.y);
      updateStarIntensity();
      linksLayer.style.transform = 'rotateX(0deg) rotateY(0deg)';
      canvas.style.transform = 'translate(0,0) scale(1)';
    });

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

    // pressed cursor state on mousedown/mouseup
    field.addEventListener('mousedown', function(){ field.classList.add('is-pressed'); });
    field.addEventListener('mouseup', function(){ field.classList.remove('is-pressed'); });
    field.addEventListener('mouseleave', function(){ field.classList.remove('is-pressed'); });

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
