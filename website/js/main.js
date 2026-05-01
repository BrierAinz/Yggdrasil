/* Yggdrasil Website — Main JS
   Dark Fantasy · Norse · Lovecraftian Enhancements */

(function () {
  'use strict';

  /* Mobile nav toggle */
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      const open = navLinks.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    });

    document.addEventListener('click', (e) => {
      if (!toggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* Copy-to-clipboard buttons */
  document.querySelectorAll('.copy-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const text = btn.dataset.copy;
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        const original = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.textContent = original;
          btn.classList.remove('copied');
        }, 1500);
      } catch (err) {
        /* Fallback */
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        const original = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.textContent = original;
          btn.classList.remove('copied');
        }, 1500);
      }
    });
  });

  /* Smooth scroll for anchor links */
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* Intersection Observer for scroll-triggered reveal animations */
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal-visible');
          // Stagger children if they exist
          const children = entry.target.querySelectorAll('.realm-tree-node, .feature-item, .arch-node, .callout-line');
          if (children.length > 0) {
            children.forEach((child, i) => {
              child.style.transitionDelay = `${i * 0.08}s`;
              if (!child.classList.contains('reveal-hidden')) {
                child.classList.add('reveal-hidden');
              }
              // Force reflow then add visible
              requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                  child.classList.add('reveal-visible');
                });
              });
            });
          }
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: '0px 0px -30px 0px' }
  );

  /* Apply reveal-hidden to all sections and key elements */
  document.querySelectorAll('.section, .card, .workflow-card, .realm-tree-level, .arch-diagram, .feature-list, .callout, .status-table, .hero-install').forEach((el) => {
    if (!el.classList.contains('hero')) {
      el.classList.add('reveal-hidden');
      revealObserver.observe(el);
    }
  });

  /* Also observe realm-tree nodes for individual animation */
  document.querySelectorAll('.realm-tree-node').forEach((el) => {
    el.classList.add('reveal-hidden');
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  });

  /* Nav background enhancement on scroll */
  const nav = document.getElementById('top-nav');
  if (nav) {
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;
      if (scrollY > 50) {
        nav.style.background = 'rgba(10, 14, 23, 0.97)';
        nav.style.boxShadow = '0 2px 20px rgba(0,0,0,0.4)';
      } else {
        nav.style.background = 'rgba(10, 14, 23, 0.92)';
        nav.style.boxShadow = 'none';
      }
      lastScroll = scrollY;
    }, { passive: true });
  }

  /* Parallax subtle movement on rune particles */
  const runeParticles = document.querySelector('.rune-particles');
  if (runeParticles) {
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          const offset = scrollY * 0.05;
          runeParticles.style.transform = `translateY(-${offset}px)`;
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* Add eldritch shimmer effect to realm-tree-nodes on hover */
  document.querySelectorAll('.realm-tree-node').forEach((node) => {
    const borderColor = node.style.borderColor || 'var(--border)';
    node.addEventListener('mouseenter', () => {
      node.style.boxShadow = `0 0 25px ${borderColor.replace(/[^,]*\)/, '0.15)')}`;
    });
    node.addEventListener('mouseleave', () => {
      node.style.boxShadow = '';
    });
  });

  /* Active arch-diagram connector animations */
  const archArrows = document.querySelectorAll('.arch-arrow');
  archArrows.forEach((arrow, i) => {
    arrow.style.animationDelay = `${i * 0.5}s`;
  });

  /* Randomize rune particle animation speeds slightly for organic feel */
  document.querySelectorAll('.rune-particle').forEach((p) => {
    const currentDuration = parseFloat(p.style.animationDuration) || 25;
    const variation = (Math.random() - 0.5) * 4;
    p.style.animationDuration = `${currentDuration + variation}s`;

    // Randomize starting position slightly
    const currentLeft = parseFloat(p.style.left) || 50;
    p.style.left = `${currentLeft + (Math.random() - 0.5) * 3}%`;
  });

})();
