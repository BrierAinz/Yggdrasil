import React from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
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
        </div>
      </div>
    </header>
  );
}

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
