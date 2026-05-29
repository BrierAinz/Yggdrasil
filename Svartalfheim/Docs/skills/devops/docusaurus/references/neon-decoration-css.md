# Neon Decoration CSS Patterns for Docusaurus

Reusable CSS patterns for cyberpunk/neon themed docs sites. All go into `src/css/custom.css`.

## Hero Floating Runes

```css
.heroRunes {
  position: absolute;
  width: 100%;
  text-align: center;
  color: rgba(56, 189, 248, 0.15);
  font-size: 1.5rem;
  letter-spacing: 0.5rem;
  user-select: none;
  pointer-events: none;
  overflow: hidden;
}
.heroRunes--top    { top: 8px; }
.heroRunes--bottom { bottom: 8px; }

.heroRuneFloat {
  position: absolute;
  font-size: 2rem;
  color: rgba(56, 189, 248, 0.25);
  animation: runeFloat 8s ease-in-out infinite;
  user-select: none;
  pointer-events: none;
}
@keyframes runeFloat {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.25; }
  50%      { transform: translateY(-20px) rotate(10deg); opacity: 0.5; }
}
```

Usage in `index.tsx`:
```tsx
<div className="heroRunes heroRunes--top">ᚠ ᚢ ᚦ ᚨ ᚱ ᚲ ᚷ ᚹ ᚺ ᚾ ᛁ ᛃ ᛇ ᛈ ᛉ ᛊ ᛏ ᛒ ᛖ ᛗ ᛚ ᛜ ᛞ ᛟ</div>
<div className="heroRuneFloat" style={{left:'10%', animationDelay:'0s'}}>ᚠ</div>
<div className="heroRuneFloat" style={{left:'30%', animationDelay:'1.5s'}}>ᛊ</div>
```

## Scanline Overlay (CRT Effect)

```css
.scanlineOverlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg, transparent, transparent 2px,
    rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px
  );
  z-index: 1;
}
```

## Gradient Card Borders (Animated)

```css
.heroCard {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(56, 189, 248, 0.15);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.heroCard:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(56, 189, 248, 0.15), 0 0 0 1px rgba(56, 189, 248, 0.3);
}
/* Use staggered animation-delay on each card: 0s, 0.2s, 0.4s, etc. */
.heroCard::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 14px;
  background: conic-gradient(from var(--card-angle, 0deg), #38bdf8, #d946ef, #fbbf24, #38bdf8);
  z-index: -1;
  opacity: 0;
  transition: opacity 0.3s ease;
  animation: rotateGradient 4s linear infinite;
}
.heroCard:hover::before { opacity: 1; }

@keyframes rotateGradient {
  from { --card-angle: 0deg; }
  to   { --card-angle: 360deg; }
}
```

**Note**: CSS `@property` for custom properties with animation requires browser support. Simpler alternative — just animate `filter: hue-rotate()`:

```css
.heroCard:hover {
  box-shadow: 0 0 20px rgba(56,189,248,0.2), 0 0 60px rgba(217,70,239,0.1);
  animation: cardGlow 3s ease-in-out infinite;
}
@keyframes cardGlow {
  0%, 100% { box-shadow: 0 0 20px rgba(56,189,248,0.2), 0 0 60px rgba(217,70,239,0.1); }
  50%      { box-shadow: 0 0 30px rgba(56,189,248,0.3), 0 0 80px rgba(217,70,239,0.15); }
}
```

## Sidebar Hover Glow

```css
.menu__list-item:hover {
  background: rgba(56, 189, 248, 0.08) !important;
  box-shadow: inset 3px 0 12px -4px rgba(56, 189, 248, 0.25);
  border-left: 2px solid #38bdf8;
  margin-left: -2px;
  padding-left: calc(1rem + 2px);
}
.menu__link--active {
  box-shadow: inset 3px 0 15px -4px rgba(56, 189, 248, 0.3), 0 0 8px rgba(56, 189, 248, 0.15);
}
```

## TOC Neon Ticks

```css
.table-of-contents__link--active {
  color: #38bdf8 !important;
  position: relative;
}
.table-of-contents__link--active::before {
  content: '';
  position: absolute; left: -1rem; top: 50%;
  transform: translateY(-50%);
  width: 4px; height: 4px; border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 6px #38bdf8, 0 0 12px rgba(56,189,248,0.5);
  animation: tocPulse 2s ease-in-out infinite;
}
@keyframes tocPulse {
  0%, 100% { box-shadow: 0 0 6px #38bdf8, 0 0 12px rgba(56,189,248,0.5); }
  50%      { box-shadow: 0 0 8px #38bdf8, 0 0 20px rgba(56,189,248,0.7), 0 0 30px rgba(217,70,239,0.3); }
}
```

## Custom Admonition Styles

```css
/* Realm — cyan glow */
.admonition-realm {
  border-left-color: #38bdf8 !important;
  background: linear-gradient(135deg, rgba(56,189,248,0.08), rgba(56,189,248,0.02)) !important;
  box-shadow: 0 0 20px rgba(56,189,248,0.1), inset 0 0 20px rgba(56,189,248,0.03);
}
.admonition-realm .admonition-heading { color: #38bdf8 !important; font-family: 'Cinzel', serif; }
.admonition-realm .admonition-heading::before { content: 'ᛊ '; filter: drop-shadow(0 0 4px rgba(56,189,248,0.5)); }

/* Neon — magenta glow */
.admonition-neon {
  border-left-color: #d946ef !important;
  background: linear-gradient(135deg, rgba(217,70,239,0.08), rgba(217,70,239,0.02)) !important;
  box-shadow: 0 0 20px rgba(217,70,239,0.1), inset 0 0 20px rgba(217,70,239,0.03);
}
.admonition-neon .admonition-heading { color: #d946ef !important; }
.admonition-neon .admonition-heading::before { content: '⚡ '; }

/* Runic — gold glow */
.admonition-runic {
  border-left-color: #fbbf24 !important;
  background: linear-gradient(135deg, rgba(251,191,36,0.08), rgba(251,191,36,0.02)) !important;
  box-shadow: 0 0 20px rgba(251,191,36,0.1), inset 0 0 20px rgba(251,191,36,0.03);
}
.admonition-runic .admonition-heading { color: #fbbf24 !important; }
.admonition-runic .admonition-heading::before { content: 'ᚱ '; }
```

## Page Transition Fade

```css
.main-wrapper {
  animation: fadeInPage 0.3s ease-out;
}
@keyframes fadeInPage {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

## Glow Pulse Headings

```css
@keyframes glowBreathe {
  0%, 100% { text-shadow: 0 0 10px rgba(56,189,248,0.3), 0 0 20px rgba(56,189,248,0.1); }
  50%      { text-shadow: 0 0 15px rgba(56,189,248,0.5), 0 0 30px rgba(56,189,248,0.2); }
}
h1 { animation: glowBreathe 4s ease-in-out infinite; }
```