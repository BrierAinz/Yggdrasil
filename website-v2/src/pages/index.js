import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import Link from '@docusaurus/Link';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className="hero hero--dark">
      <div className="container">
        <div style={{textAlign: 'center', padding: '3rem 0'}}>
          <img
            src="/Yggdrasil/img/logo-yggdrasil.svg"
            alt="Yggdrasil"
            style={{height: '80px', marginBottom: '1.5rem', filter: 'drop-shadow(0 0 20px rgba(200, 162, 62, 0.4))'}}
          />
          <Heading as="h1" className="hero__title" style={{color: '#c8a23e'}}>
            Yggdrasil
          </Heading>
          <p className="hero__subtitle" style={{fontSize: '1.3rem', maxWidth: '600px', margin: '0 auto 2rem'}}>
            A personal project ecosystem rooted in Norse mythology. Nine realms. One tree.
          </p>
          <div style={{display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap'}}>
            <Link
              className="button button--primary button--lg"
              to="/docs/intro"
              style={{backgroundColor: '#c8a23e', borderColor: '#c8a23e', color: '#1a1b26', fontWeight: 600}}
            >
              Explore the Realms
            </Link>
            <Link
              className="button button--outline button--lg"
              to="/docs/setup"
              style={{borderColor: '#c8a23e', color: '#c8a23e'}}
            >
              Get Started
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}

const realms = [
  {name: 'Asgard', color: '#c8a23e', desc: 'Core technology — Lilith v5, Swarm, API, Memory, CLI, Gateway'},
  {name: 'Vanaheim', color: '#e06c75', desc: 'AI agents — Pantheon of VanirAgent personalities'},
  {name: 'Alfheim', color: '#61afef', desc: 'UI prototypes — TerminalDashboard, HTMX experiments'},
  {name: 'Muspelheim', color: '#e5c07b', desc: 'Active development — ForgeMaster, Eir, AutoSub'},
  {name: 'Svartalfheim', color: '#98c379', desc: 'Knowledge — Plans, docs, research findings'},
  {name: 'Niflheim', color: '#56b6c2', desc: 'Resources — Models, datasets, assets'},
  {name: 'Midgard', color: '#c678dd', desc: 'Personal apps — Finance, habits, recipes'},
  {name: 'Jotunheim', color: '#d19a66', desc: 'Massive projects — long-term endeavors'},
  {name: 'Helheim', color: '#be5046', desc: 'Archive — deprecated code, graveyard'},
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
          <Heading as="h2" style={{color: '#c8a23e', textAlign: 'center', marginBottom: '2rem'}}>
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
                  <img
                    src={`/Yggdrasil/img/realm-${realm.name.toLowerCase()}.svg`}
                    alt={realm.name}
                    style={{width: '36px', height: '36px'}}
                  />
                  <strong style={{color: realm.color, fontSize: '1.1rem'}}>{realm.name}</strong>
                </div>
                <p style={{margin: 0, opacity: 0.85, fontSize: '0.9rem'}}>{realm.desc}</p>
              </div>
            ))}
          </div>
        </section>
        <section style={{textAlign: 'center', padding: '2rem 0', borderTop: '1px solid rgba(200, 162, 62, 0.2)'}}>
          <p style={{opacity: 0.7, fontSize: '0.85rem'}}>
            Built with runes and code. Powered by Lilith v5.
          </p>
        </section>
      </main>
    </Layout>
  );
}
