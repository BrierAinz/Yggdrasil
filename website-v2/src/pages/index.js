import React from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Translate, {translate} from '@docusaurus/Translate';
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
            <Translate id="homepage.cta.explore">ᚨ Explore the Realms</Translate>
          </Link>
          <Link className="button button--outline button--lg" to="/docs/setup" style={{marginLeft: '1rem'}}>
            <Translate id="homepage.cta.start">ᛏ Get Started</Translate>
          </Link>
        </div>
      </div>
    </header>
  );
}

const Realms = {
  en: [
    {rune: 'ᚨ', name: 'Asgard', desc: 'Core Technology — Lilith, Gateway, LLM providers'},
    {rune: 'ᚹ', name: 'Vanaheim', desc: 'AI Agents — Bots, agent profiles, protocols'},
    {rune: 'ᛇ', name: 'Alfheim', desc: 'UI Prototypes — Visual experiments, dashboards'},
    {rune: 'ᛗ', name: 'Svartalfheim', desc: 'Knowledge — Docs, ADRs, deployment guides'},
    {rune: 'ᚦ', name: 'Muspelheim', desc: 'Active Dev — Sprints, hotfixes, experiments'},
    {rune: 'ᛚ', name: 'Niflheim', desc: 'Resources — Datasets, models, training data'},
    {rune: 'ᛊ', name: 'Helheim', desc: 'Graveyard — Archived code, legacy versions'},
    {rune: 'ᛏ', name: 'Jotunheim', desc: 'Massive — Long-term, large-scope projects'},
    {rune: 'ᛒ', name: 'Midgard', desc: 'Personal — Completed, battle-tested apps'},
  ],
  es: [
    {rune: 'ᚨ', name: 'Asgard', desc: 'Tecnología Core — Lilith, Gateway, proveedores LLM'},
    {rune: 'ᚹ', name: 'Vanaheim', desc: 'Agentes IA — Bots, perfiles de agentes, protocolos'},
    {rune: 'ᛇ', name: 'Alfheim', desc: 'Prototipos UI — Experimentos visuales, dashboards'},
    {rune: 'ᛗ', name: 'Svartalfheim', desc: 'Conocimiento — Docs, ADRs, guías de deploy'},
    {rune: 'ᚦ', name: 'Muspelheim', desc: 'Desarrollo Activo — Sprints, hotfixes, experimentos'},
    {rune: 'ᛚ', name: 'Niflheim', desc: 'Recursos — Datasets, modelos, datos de entrenamiento'},
    {rune: 'ᛊ', name: 'Helheim', desc: 'Cementerio — Código archivado, versiones legacy'},
    {rune: 'ᛏ', name: 'Jotunheim', desc: 'Masivo — Proyectos de largo plazo, gran alcance'},
    {rune: 'ᛒ', name: 'Midgard', desc: 'Personal — Apps completadas y probadas en batalla'},
  ],
};

function RealmGrid() {
  const {i18n} = useDocusaurusContext();
  const locale = i18n.currentLocale;
  const realms = Realms[locale] || Realms.en;

  return (
    <section className={styles.realms}>
      <div className="container">
        <h2 style={{textAlign: 'center', marginBottom: '2rem'}}>
          <Translate id="homepage.realms.title">᛭ The Nine Realms</Translate>
        </h2>
        <div className={styles.realmGrid}>
          {realms.map((r) => (
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
