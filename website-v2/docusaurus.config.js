// @ts-check

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Yggdrasil',
  tagline: 'Nine Realms. One Tree. Infinite Possibilities.',
  favicon: 'img/favicon.svg',

  url: 'https://docs.brierstudios.com',
  baseUrl: '/',

  organizationName: 'BrierAinz',
  projectName: 'Yggdrasil',

  onBrokenLinks: 'throw',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'es'],
    localeConfigs: {
      en: { htmlLang: 'en-US' },
      es: { htmlLang: 'es-ES', label: 'Español' },
    },
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/BrierAinz/Yggdrasil/tree/master/website-v2/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/hero-yggdrasil.svg',
      navbar: {
        title: 'YGGDRASIL',
        logo: {
          alt: 'Yggdrasil Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Docs',
          },
          {
            href: 'https://github.com/BrierAinz/Yggdrasil',
            label: 'GitHub',
            position: 'right',
          },
          {
            type: 'localeDropdown',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              { label: 'Overview', to: '/docs/intro' },
              { label: 'Architecture', to: '/docs/architecture' },
              { label: 'Setup', to: '/docs/setup' },
            ],
          },
          {
            title: 'Agents',
            items: [
              { label: 'Lilith', to: '/docs/lilith' },
              { label: 'Changelog', to: '/docs/changelog' },
            ],
          },
          {
            title: 'More',
            items: [
              { label: 'GitHub', href: 'https://github.com/BrierAinz/Yggdrasil' },
              { label: 'BrierStudios', href: 'https://brierstudios.com' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} BrierStudios. Built with Docusaurus.`,
      },
      prism: {
        theme: require('prism-react-renderer').themes.github,
        darkTheme: require('prism-react-renderer').themes.dracula,
        additionalLanguages: ['bash', 'python', 'json'],
      },
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      announcementBar: {
        id: 'support_us',
        content: '᛭ Yggdrasil v5.1 — Lilith reforged into modular packages',
        backgroundColor: '#1a1a2e',
        textColor: '#c9a84c',
        isCloseable: true,
      },
    }),
};

module.exports = config;
