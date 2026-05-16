import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Hybrid Memory',
    rune: 'ᛒ',
    color: '#c8a23e',
    description: (
      <>
        Three-layer memory: vector embeddings, knowledge graph, and full-text search.
        The agent remembers who you are and what you did — no context lost between sessions.
      </>
    ),
  },
  {
    title: 'Swarm Intelligence',
    rune: 'ᚹ',
    color: '#b87333',
    description: (
      <>
        Spawn LLM-powered specialist agents — researcher, coder, writer, critic —
        each with its own context and tools. Parallel execution with file locking and session persistence.
      </>
    ),
  },
  {
    title: 'Forge-Ready CLI',
    rune: 'ᛏ',
    color: '#d19a66',
    description: (
      <>
        Control from terminal or Telegram. Skills with hot-reload, multi-provider LLM fallback,
        batch mode, and TOML configuration. Your forge, your rules.
      </>
    ),
  },
];

function Feature({rune, title, description, color}) {
  return (
    <div className={clsx('col col--4')}>
      <div style={{textAlign: 'center', marginBottom: '1rem'}}>
        <span style={{fontSize: '3rem', color: color, fontFamily: "'MedievalSharp', cursive", lineHeight: 1}}>
          {rune}
        </span>
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3" style={{fontFamily: "'Cinzel', serif", color: color}}>{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}