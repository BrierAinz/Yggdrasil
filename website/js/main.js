/* Yggdrasil Website — Main JS
   Dark Fantasy · Norse · Lovecraftian Mega-Enhancements */

(function () {
  'use strict';

  /* ============================================
     1. LOADING SCREEN DISMISS
     ============================================ */
  const loadingScreen = document.getElementById('loading-screen');

  function dismissLoadingScreen() {
    if (!loadingScreen) return;
    loadingScreen.classList.add('hidden');
    // Trigger typewriter after loading
    setTimeout(initTypewriter, 300);
    setTimeout(() => {
      if (loadingScreen.parentNode) loadingScreen.parentNode.removeChild(loadingScreen);
    }, 1000);
  }

  // Dismiss after 2.5s or when all resources loaded
  let loadingTimeout = setTimeout(dismissLoadingScreen, 2500);

  window.addEventListener('load', () => {
    clearTimeout(loadingTimeout);
    // Give a minimum display time of 1.5s for the loading animation
    setTimeout(dismissLoadingScreen, 1500);
  });

  /* ============================================
     2. CANVAS PARTICLE SYSTEM
     ============================================ */
  const canvas = document.getElementById('particles-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let particles = [];
    let mouseX = -1000, mouseY = -1000;
    let animFrameId;

    const RUNE_CHARS = ['ᚱ', 'ᛏ', 'ᚻ', 'ᛖ', 'ᛉ', 'ᛗ', '᛭', '᛫', 'ᚺ', '᛬'];
    const SYMBOL_CHARS = ['∘', '◦', '•', '✦', '⟡', '◈', '⟐', '⬡'];

    function resizeCanvas() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    class Particle {
      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * canvas.width;
        this.y = canvas.height + Math.random() * 100;
        this.speed = 0.15 + Math.random() * 0.4;
        this.drift = (Math.random() - 0.5) * 0.3;
        this.size = 8 + Math.random() * 14;
        this.opacity = 0.02 + Math.random() * 0.06;
        this.baseOpacity = this.opacity;
        this.rotation = Math.random() * 360;
        this.rotSpeed = (Math.random() - 0.5) * 0.5;
        this.layer = Math.floor(Math.random() * 3); // 0=far, 1=mid, 2=near
        this.layer *= 0.4;
        this.speed += this.layer;

        // Decide type: rune, dot, or symbol
        const rand = Math.random();
        if (rand < 0.4) {
          this.type = 'rune';
          this.char = RUNE_CHARS[Math.floor(Math.random() * RUNE_CHARS.length)];
          const colorRand = Math.random();
          if (colorRand < 0.5) {
            this.color = { r: 199, g: 164, b: 74 }; // gold
          } else if (colorRand < 0.8) {
            this.color = { r: 170, g: 85, b: 255 }; // eldritch
          } else {
            this.color = { r: 0, g: 255, b: 136 }; // necrotic
          }
        } else if (rand < 0.7) {
          this.type = 'dot';
          this.size = 1 + Math.random() * 2;
          this.color = { r: 199, g: 164, b: 74 };
        } else {
          this.type = 'symbol';
          this.char = SYMBOL_CHARS[Math.floor(Math.random() * SYMBOL_CHARS.length)];
          this.color = { r: 170, g: 85, b: 255 };
        }
      }

      update(scrollY) {
        // Parallax: different speeds per layer
        const parallaxSpeed = 0.3 + this.layer;
        this.y -= this.speed * parallaxSpeed;
        this.x += this.drift;
        this.rotation += this.rotSpeed;

        // Mouse proximity glow
        const dx = this.x - mouseX;
        const dy = this.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 150) {
          const factor = 1 - (dist / 150);
          this.opacity = this.baseOpacity + factor * 0.12;
          // Push away slightly
          if (dist > 1) {
            this.x += (dx / dist) * factor * 0.5;
            this.y += (dy / dist) * factor * 0.5;
          }
        } else {
          this.opacity = this.baseOpacity;
        }

        // Scroll parallax
        this.y -= scrollY * 0.0001 * this.layer;

        // Reset when off screen
        if (this.y < -50 || this.x < -50 || this.x > canvas.width + 50) {
          this.reset();
        }
      }

      draw(ctx) {
        const r = this.color.r, g = this.color.g, b = this.color.b;

        if (this.type === 'dot') {
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${r},${g},${b},${this.opacity})`;
          ctx.fill();
          // Glow for nearby particles
          if (this.opacity > this.baseOpacity) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${r},${g},${b},${this.opacity * 0.3})`;
            ctx.fill();
          }
        } else {
          ctx.save();
          ctx.translate(this.x, this.y);
          ctx.rotate((this.rotation * Math.PI) / 180);
          ctx.font = `${this.size}px 'Inter', sans-serif`;
          ctx.fillStyle = `rgba(${r},${g},${b},${this.opacity})`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          // Text shadow glow
          if (this.opacity > this.baseOpacity * 1.5) {
            ctx.shadowColor = `rgba(${r},${g},${b},${this.opacity * 3})`;
            ctx.shadowBlur = 15;
          }

          ctx.fillText(this.char, 0, 0);
          ctx.restore();
        }
      }
    }

    // Create particles
    const PARTICLE_COUNT = window.innerWidth < 768 ? 15 : 55;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const p = new Particle();
      p.y = Math.random() * canvas.height; // Start distributed
      particles.push(p);
    }

    let currentScrollY = 0;
    window.addEventListener('scroll', () => {
      currentScrollY = window.scrollY;
    }, { passive: true });

    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    }, { passive: true });

    function animateParticles() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        p.update(currentScrollY);
        p.draw(ctx);
      });
      animFrameId = requestAnimationFrame(animateParticles);
    }

    // Start after a brief delay for performance
    setTimeout(animateParticles, 500);
  }

  /* ============================================
     3. CURSOR TRAIL
     ============================================ */
  const cursorTrail = document.getElementById('cursor-trail');
  if (cursorTrail && window.innerWidth >= 768) {
    let lastTrailTime = 0;
    const TRAIL_INTERVAL = 40; // ms between dots

    document.addEventListener('mousemove', (e) => {
      const now = Date.now();
      if (now - lastTrailTime < TRAIL_INTERVAL) return;
      lastTrailTime = now;

      const dot = document.createElement('div');
      dot.className = 'cursor-dot';
      const isGold = Math.random() > 0.5;
      const color = isGold
        ? `rgba(199, 164, 74, 0.6)`
        : `rgba(170, 85, 255, 0.5)`;
      const size = 3 + Math.random() * 5;

      dot.style.left = (e.clientX - size / 2) + 'px';
      dot.style.top = (e.clientY - size / 2) + 'px';
      dot.style.width = size + 'px';
      dot.style.height = size + 'px';
      dot.style.background = color;
      dot.style.boxShadow = `0 0 ${size * 2}px ${color}`;

      cursorTrail.appendChild(dot);

      // Remove after animation
      setTimeout(() => {
        if (dot.parentNode) dot.parentNode.removeChild(dot);
      }, 600);
    });
  }

  /* ============================================
     4. SCROLL PROGRESS BAR
     ============================================ */
  const progressBar = document.getElementById('scroll-progress-bar');
  const updateProgress = () => {
    if (!progressBar) return;
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    progressBar.style.width = progress + '%';
  };

  window.addEventListener('scroll', updateProgress, { passive: true });
  updateProgress();

  /* ============================================
     5. TYPEWRITER EFFECT on hero h1
     ============================================ */
  function initTypewriter() {
    const heroTitle = document.querySelector('.hero-title[data-typewriter]');
    if (!heroTitle) return;

    const fullText = heroTitle.textContent.trim();
    heroTitle.textContent = '';
    heroTitle.style.opacity = '1';

    let charIndex = 0;
    const typeInterval = setInterval(() => {
      if (charIndex < fullText.length) {
        heroTitle.textContent += fullText[charIndex];
        charIndex++;
      } else {
        clearInterval(typeInterval);
      }
    }, 70);
  }

  /* ============================================
     6. INTERSECTION OBSERVER for scroll reveals
     ============================================ */
  const revealElements = document.querySelectorAll('.reveal, .reveal-hidden');

  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          // Stagger delay based on index among siblings
          const parent = el.parentElement;
          const siblings = parent ? Array.from(parent.querySelectorAll('.reveal-hidden, .reveal')) : [];
          const index = siblings.indexOf(el);

          el.style.transitionDelay = `${index * 0.08}s`;
          el.classList.add('reveal-visible');

          // Also stagger children
          const children = el.querySelectorAll('.realm-tree-node, .feature-item, .arch-node, .callout-line');
          if (children.length > 0) {
            children.forEach((child, i) => {
              child.style.transitionDelay = `${0.08 + i * 0.08}s`;
              if (!child.classList.contains('reveal-hidden')) {
                child.classList.add('reveal-hidden');
              }
              requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                  child.classList.add('reveal-visible');
                });
              });
            });
          }

          revealObserver.unobserve(el);
        }
      });
    },
    { threshold: 0.08, rootMargin: '0px 0px -30px 0px' }
  );

  revealElements.forEach(el => {
    if (!el.classList.contains('reveal-visible')) {
      revealObserver.observe(el);
    }
  });

  // Also observe realm-tree nodes individually
  document.querySelectorAll('.realm-tree-node').forEach(el => {
    el.classList.add('reveal-hidden');
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    revealObserver.observe(el);
  });

  /* ============================================
     7. 3D TILT EFFECT on realm-tree-node and feature-item
     ============================================ */
  if (window.matchMedia('(hover: hover)').matches) {
    const tiltElements = document.querySelectorAll('.realm-tree-node, .feature-item');

    tiltElements.forEach(el => {
      el.addEventListener('mousemove', (e) => {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const rotateX = ((y - centerY) / centerY) * -8; // degrees
        const rotateY = ((x - centerX) / centerX) * 8;

        el.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
      });

      el.addEventListener('mouseleave', () => {
        el.style.transform = '';
      });
    });
  }

  /* ============================================
     8. NAV ACTIVE LINK based on scroll position
     ============================================ */
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link[data-section]');

  function updateActiveNav() {
    const scrollY = window.scrollY + 100;
    let currentSection = '';

    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      if (scrollY >= sectionTop && scrollY < sectionTop + sectionHeight) {
        currentSection = section.getAttribute('id');
      }
    });

    navLinks.forEach(link => {
      link.classList.remove('active');
      if (link.dataset.section === currentSection) {
        link.classList.add('active');
      }
    });
  }

  window.addEventListener('scroll', updateActiveNav, { passive: true });

  /* ============================================
     9. NAV SCROLL ENHANCEMENT (glass effect)
     ============================================ */
  const nav = document.getElementById('top-nav');
  if (nav) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 50) {
        nav.classList.add('scrolled');
        nav.style.background = 'rgba(10, 14, 23, 0.97)';
        nav.style.boxShadow = '0 2px 20px rgba(0,0,0,0.4)';
      } else {
        nav.classList.remove('scrolled');
        nav.style.background = 'rgba(10, 14, 23, 0.85)';
        nav.style.boxShadow = 'none';
      }
    }, { passive: true });
  }

  /* ============================================
     10. MAGNETIC BUTTONS
     ============================================ */
  if (window.matchMedia('(hover: hover)').matches) {
    const magneticEls = document.querySelectorAll('.nav-github, .copy-btn');

    magneticEls.forEach(el => {
      el.addEventListener('mousemove', (e) => {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        const distance = Math.sqrt(x * x + y * y);
        const maxDist = 80;

        if (distance < maxDist) {
          const factor = 1 - (distance / maxDist);
          el.style.transform = `translate(${x * factor * 0.2}px, ${y * factor * 0.2}px)`;
        }
      });

      el.addEventListener('mouseleave', () => {
        el.style.transform = '';
      });
    });
  }

  /* ============================================
     11. GLITCH EFFECT on hero h1
     ============================================ */
  const heroTitle = document.querySelector('.hero-title');
  if (heroTitle) {
    function triggerGlitch() {
      heroTitle.classList.add('glitching');
      setTimeout(() => {
        heroTitle.classList.remove('glitching');
      }, 300);

      // Schedule next glitch
      const nextDelay = 8000 + Math.random() * 12000; // 8-20s
      setTimeout(triggerGlitch, nextDelay);
    }

    // First glitch after 6s
    setTimeout(triggerGlitch, 6000);
  }

  /* ============================================
     12. ROW HOVER SLIDE on status table
     ============================================ */
  document.querySelectorAll('.status-table tbody tr').forEach(row => {
    row.addEventListener('mouseenter', () => {
      row.style.transform = 'scale(1.005)';
      row.style.transition = 'all 0.3s ease';
    });
    row.addEventListener('mouseleave', () => {
      row.style.transform = '';
    });
  });

  /* ============================================
     13. PARALLAX on rune particles (CSS ones)
     ============================================ */
  const runeParticles = document.querySelector('.rune-particles');
  if (runeParticles) {
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          const offset = scrollY * 0.05;

          // Move CSS rune particles at different rates (3 layers)
          const particles = runeParticles.querySelectorAll('.rune-particle');
          particles.forEach((p, i) => {
            const layer = i % 3; // 0, 1, 2
            const speed = 0.02 + layer * 0.03;
            const yOffset = scrollY * speed;
            p.style.transform = `translateY(-${yOffset}px)`;
          });

          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ============================================
     14. Mobile nav toggle
     ============================================ */
  const toggle = document.querySelector('.nav-toggle');
  const navLinksEl = document.querySelector('.nav-links');

  if (toggle && navLinksEl) {
    toggle.addEventListener('click', () => {
      const open = navLinksEl.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    });

    document.addEventListener('click', (e) => {
      if (!toggle.contains(e.target) && !navLinksEl.contains(e.target)) {
        navLinksEl.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ============================================
     15. Copy-to-clipboard buttons
     ============================================ */
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

  /* ============================================
     16. Smooth scroll for anchor links
     ============================================ */
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* ============================================
     17. Realm node hover glow (using --node-color)
     ============================================ */
  document.querySelectorAll('.realm-tree-node').forEach((node) => {
    const borderColor = node.style.borderColor || 'var(--border)';
    node.addEventListener('mouseenter', () => {
      const glowColor = borderColor.replace(/[^,]*\)/, '0.15)');
      node.style.boxShadow = `0 0 25px ${glowColor}, 0 0 50px ${borderColor.replace(/[^,]*\)/, '0.06)')}`;
    });
    node.addEventListener('mouseleave', () => {
      node.style.boxShadow = '';
    });
  });

  /* ============================================
     18. Arch diagram connector animations
     ============================================ */
  const archArrows = document.querySelectorAll('.arch-arrow');
  archArrows.forEach((arrow, i) => {
    arrow.style.animationDelay = `${i * 0.5}s`;
  });

  /* ============================================
     19. Randomize rune particle speeds
     ============================================ */
  document.querySelectorAll('.rune-particle').forEach((p) => {
    const currentDuration = parseFloat(p.style.animationDuration) || 25;
    const variation = (Math.random() - 0.5) * 4;
    p.style.animationDuration = `${currentDuration + variation}s`;

    const currentLeft = parseFloat(p.style.left) || 50;
    p.style.left = `${currentLeft + (Math.random() - 0.5) * 3}%`;
  });

  /* ============================================
     20. FOOTER RUNE LIGHT-UP on scroll
     ============================================ */
  const footerRunes = document.querySelectorAll('.footer-rune-divider span');
  if (footerRunes.length > 0) {
    const footerObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          footerRunes.forEach((span, i) => {
            setTimeout(() => {
              span.style.opacity = '0.8';
              span.style.textShadow = '0 0 12px rgba(199,164,74,0.6), 0 0 25px rgba(170,85,255,0.3)';
              span.style.color = 'var(--parchment)';
              setTimeout(() => {
                span.style.opacity = '';
                span.style.textShadow = '';
                span.style.color = '';
              }, 800);
            }, i * 150);
          });
        }
      });
    }, { threshold: 0.5 });

    const footerEl = document.querySelector('.site-footer');
    if (footerEl) footerObserver.observe(footerEl);
  }

  /* ============================================
     21. SECTION DIVIDER RUNE WAVE
     ============================================ */
  document.querySelectorAll('.section').forEach(section => {
    const divider = section.querySelector('.section::before');
    // CSS handles the wave animation, but we can add intersection observer for enhanced effect
    const sectionObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.setProperty('--section-visible', '1');
        }
      });
    }, { threshold: 0.1 });

    sectionObserver.observe(section);
  });

})();
