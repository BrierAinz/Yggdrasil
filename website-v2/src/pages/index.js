import React from 'react';
<<<<<<< HEAD
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import styles from './index.module.css';
=======
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import Link from '@docusaurus/Link';
>>>>>>> origin/main

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
<<<<<<< HEAD
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link className="button button--secondary button--lg" to="/docs/intro">
            ᚨ Explore the Realms
          </Link>
          <Link className="button button--outline button--lg" to="/docs/setup" style={{marginLeft: '1rem'}}>
            ᛏ Get Started
          </Link>
=======
    <header className="hero hero--dark">
      <div className="container">
        <div style={{textAlign: 'center', padding: '3rem 0'}}>
          <img
            src="/img/logo-yggdrasil.svg"
            alt="Yggdrasil"
            style={{height: '80px', marginBottom: '1.5rem', filter: 'drop-shadow(0 0 20px rgba(200, 162, 62, 0.4))'}}
          />
          <Heading as="h1" className="hero__title" style={{color: '#c8a23e', fontFamily: "'Cinzel', serif"}}>
            ᛭ Yggdrasil
          </Heading>
          <p className="hero__subtitle" style={{fontSize: '1.3rem', maxWidth: '600px', margin: '0 auto 2rem'}}>
            A personal project ecosystem rooted in Norse mythology. Nine realms. One tree. Forged in ancient iron.
          </p>
          <div style={{display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap'}}>
            <Link
              className="button button--primary button--lg"
              to="/docs/intro"
              style={{backgroundColor: '#c8a23e', borderColor: '#c8a23e', color: '#1a1b26', fontWeight: 600, fontFamily: "'Cinzel', serif"}}
            >
              ᚨ Explore the Realms
            </Link>
            <Link
              className="button button--outline button--lg"
              to="/docs/setup"
              style={{borderColor: '#c8a23e', color: '#c8a23e', fontFamily: "'Cinzel', serif"}}
            >
              ᛏ Get Started
            </Link>
          </div>
>>>>>>> origin/main
        </div>
      </div>
    </header>
  );
}

<<<<<<< HEAD
const Realms = [
  {rune: 'ᚨ', name: 'Asgard', desc: 'Core Technology — Lilith, Gateway, LLM providers'},
  {rune: 'ᚹ', name: 'Vanaheim', desc: 'AI Agents — Bots, agent profiles, protocols'},
  {rune: 'ᛇ', name: 'Alfheim', desc: 'UI Prototypes — Visual experiments, dashboards'},
  {rune: 'ᛗ', name: 'Svartalfheim', desc: 'Knowledge — Docs, ADRs, deployment guides'},
  {rune: 'ᚦ', name: 'Muspelheim', desc: 'Active Dev — Sprints, hotfixes, experiments'},
  {rune: 'ᛚ', name: 'Niflheim', desc: 'Resources — Datasets, models, training data'},
  {rune: 'ᛊ', name: 'Helheim', desc: 'Graveyard — Archived code, legacy versions'},
  {rune: 'ᛏ', name: 'Jotunheim', desc: 'Massive — Long-term, large-scope projects'},
  {rune: 'ᛒ', name: 'Midgard', desc: 'Personal — Completed, battle-tested apps'},
];

function RealmGrid() {
  return (
    <section className={styles.realms}>
      <div className="container">
        <h2 style={{textAlign: 'center', marginBottom: '2rem'}}>
          ᛭ The Nine Realms
        </h2>
        <div className={styles.realmGrid}>
          {Realms.map((r) => (
            <div key={r.name} className={styles.realmCard}>
              <span className={styles.realmRune}>{r.rune}</span>
              <strong>{r.name}</strong>
              <p>{r.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <HomepageHeader />
      <main>
        <RealmGrid />
      </main>
    </Layout>
  );
}
=======
const realms = [
  {name: 'Asgard', color: '#c8a23e', rune: 'ᚨ', desc: 'Core technology — Lilith v5, Swarm, API, Memory, CLI, Gateway'},
  {name: 'Vanaheim', color: '#b87333', rune: 'ᚹ', desc: 'AI agents — Pantheon of VanirAgent personalities'},
  {name: 'Alfheim', color: '#a8c4d4', rune: 'ᛇ', desc: 'UI prototypes — TerminalDashboard, HTMX experiments'},
  {name: 'Muspelheim', color: '#d4760a', rune: 'ᚦ', desc: 'Active development — ForgeMaster, Eir, AutoSub'},
  {name: 'Svartalfheim', color: '#e0c878', rune: 'ᚺ', desc: 'Knowledge — Plans, docs, research findings'},
  {name: 'Niflheim', color: '#7a8599', rune: 'ᛚ', desc: 'Resources — Models, datasets, assets'},
  {name: 'Midgard', color: '#6b8f71', rune: 'ᛗ', desc: 'Personal apps — Finance, habits, recipes'},
  {name: 'Jotunheim', color: '#d19a66', rune: 'ᛏ', desc: 'Massive projects — long-term endeavors'},
  {name: 'Helheim', color: '#8b2020', rune: 'ᛊ', desc: 'Archive — deprecated code, graveyard'},
];

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="Yggdrasil — A personal project ecosystem rooted in Norse mythology"
    >
      <HomepageHeader />
      <main style={{maxWidth: '1100px', margin: '0 auto', padding: '3rem 1rem'}}>
        <section style={{marginBottom: '3rem'}}>
          <Heading as="h2" style={{color: '#c8a23e', textAlign: 'center', marginBottom: '2rem', fontFamily: "'Cinzel', serif"}}>
            The Nine Realms
          </Heading>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '1rem',
          }}>
            {realms.map((realm) => (
              <div key={realm.name} style={{
                background: 'var(--ifm-background-color)',
                border: `1px solid ${realm.color}33`,
                borderRadius: '8px',
                padding: '1.25rem',
                transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
              }}>
                <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem'}}>
                  <span style={{fontSize: '1.5rem', color: realm.color, fontFamily: "'MedievalSharp', cursive"}}>{realm.rune}</span>
                  <strong style={{color: realm.color, fontSize: '1.1rem', fontFamily: "'Cinzel', serif"}}>{realm.name}</strong>
                </div>
                <p style={{margin: 0, opacity: 0.85, fontSize: '0.9rem'}}>{realm.desc}</p>
              </div>
            ))}
          </div>
        </section>
        <section style={{textAlign: 'center', padding: '2rem 0', borderTop: '1px solid rgba(200, 162, 62, 0.2)'}}>
          <p style={{opacity: 0.7, fontSize: '0.85rem'}}>
            ᛒ Forged with runes and code. Powered by Lilith v5.
          </p>
        </section>
      </main>
    </Layout>
  );
}
>>>>>>> origin/main
