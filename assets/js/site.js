(function(){
  var nav = document.querySelector('.navbar');
  if(nav){
    var onScroll = function(){
      if(window.scrollY > 24) nav.classList.add('is-scrolled');
      else nav.classList.remove('is-scrolled');
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

    function resize(){
      w = host.clientWidth; h = host.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
      ctx.setTransform(dpr,0,0,dpr,0,0);
      var count = Math.round((w * h) / (opts.density || 9000));
      bgStars = [];
      for(var i=0;i<count;i++){
        bgStars.push({
          x: Math.random()*w, y: Math.random()*h,
          r: Math.random()*1.2 + 0.3,
          phase: Math.random()*Math.PI*2,
          speed: 0.5 + Math.random()*1.2
        });
      }
    }

    var t = 0;
    function draw(){
      t += 0.016;
      ctx.clearRect(0,0,w,h);
      if(opts.glow && mouse.x > -999){
        var g = ctx.createRadialGradient(mouse.x,mouse.y,0,mouse.x,mouse.y,260);
        g.addColorStop(0,'rgba(43,95,217,0.16)');
        g.addColorStop(1,'rgba(43,95,217,0)');
        ctx.fillStyle = g;
        ctx.fillRect(0,0,w,h);
      }
      for(var i=0;i<bgStars.length;i++){
        var s = bgStars[i];
        var tw = 0.55 + 0.45*Math.sin(t*s.speed + s.phase);
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI*2);
        ctx.fillStyle = 'rgba(255,255,255,' + (0.25 + 0.55*tw) + ')';
        ctx.fill();
      }
      requestAnimationFrame(draw);
    }

    resize();
    requestAnimationFrame(draw);
    window.addEventListener('resize', resize);
    return {
      setMouse: function(x,y){ mouse.x = x; mouse.y = y; }
    };
  }

  // ambient, non-interactive starfield behind the hero
  var heroField = document.querySelector('.hero-starfield');
  if(heroField){
    var heroCanvas = heroField.querySelector('canvas');
    paintTwinklingStars(heroCanvas, heroField, {density:12000, glow:false});
  }

  // interactive project starfield
  var field = document.querySelector('.starfield-section');
  if(field){
    var canvas = field.querySelector('.starfield-canvas');
    var linksLayer = field.querySelector('.starfield-links');
    var mouse = {x:-9999,y:-9999};
    var renderer = paintTwinklingStars(canvas, field, {density:9000, glow:true});

    // burst-in: reveal stars with a staggered "pop" once the section is in view
    var stars = linksLayer ? Array.prototype.slice.call(linksLayer.querySelectorAll('.star-link')) : [];
    if('IntersectionObserver' in window){
      var burstIO = new IntersectionObserver(function(entries){
        entries.forEach(function(entry){
          if(entry.isIntersecting){
            stars.forEach(function(star, i){
              setTimeout(function(){ star.classList.add('is-burst'); }, 40 * i);
            });
            burstIO.disconnect();
          }
        });
      }, {threshold:0.15});
      burstIO.observe(field);
    } else {
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
    var ticking = false;
    function updateStarIntensity(){
      if(ticking) return;
      ticking = true;
      requestAnimationFrame(function(){
        var rect = field.getBoundingClientRect();
        clickableStars.forEach(function(star){
          var r = star.getBoundingClientRect();
          var cx = r.left + r.width/2 - rect.left;
          var cy = r.top + r.height/2 - rect.top;
          var dist = Math.hypot(mouse.x - cx, mouse.y - cy);
          var intensity = Math.max(0, 1 - dist/240);
          var dot = star.querySelector('.star-link__dot');
          var info = star.querySelector('.star-link__info');
          if(dot){
            var scale = 1 + intensity*1.6;
            dot.style.transform = 'scale(' + scale + ')';
            dot.style.boxShadow = '0 0 ' + (6+intensity*24) + 'px ' + (1+intensity*6) + 'px rgba(255,255,255,' + (0.5+intensity*0.4) + ')';
          }
          if(info){
            info.style.opacity = String(Math.min(1, intensity*1.8));
            info.style.transform = intensity > 0.1 ? 'translateY(0)' : 'translateY(2px)';
          }
        });
        ticking = false;
      });
    }
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
