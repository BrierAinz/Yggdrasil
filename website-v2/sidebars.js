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
    'lilith',
    'changelog',
    'apps',
    'reglas-yggdrasil',
  ],
};

module.exports = sidebars;
