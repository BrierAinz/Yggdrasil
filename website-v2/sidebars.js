/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'intro',
    'architecture',
    'setup',
    {
      type: 'category',
      label: 'The Nine Realms',
      items: [
        'realms/asgard',
        'realms/vanaheim',
        'realms/alfheim',
        'realms/svartalfheim',
        'realms/muspelheim',
        'realms/niflheim',
        'realms/helheim',
        'realms/jotunheim',
        'realms/midgard',
      ],
    },
    {
      type: 'category',
      label: 'Packages',
      items: [
        'packages/index',
        'packages/lilith-core',
        'packages/lilith-memory',
        'packages/lilith-tools',
        'packages/lilith-api',
        'packages/lilith-orchestrator',
        'packages/lilith-skills',
        'packages/lilith-cli',
        'packages/lilith-bridge',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/index',
        'guides/custom-agent',
      ],
    },
    'lilith',
    'changelog',
    'apps',
    'reglas-yggdrasil',
  ],
};

module.exports = sidebars;
