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

  var reveals = document.querySelectorAll('.reveal');
  if('IntersectionObserver' in window && reveals.length){
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(entry.isIntersecting){
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, {threshold:0.2});
    reveals.forEach(function(el){ io.observe(el); });
  } else {
    reveals.forEach(function(el){ el.classList.add('is-visible'); });
  }
})();
