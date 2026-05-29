// @ts-check
<<<<<<< HEAD
=======
import {themes as prismThemes} from 'prism-react-renderer';
>>>>>>> origin/main

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Yggdrasil',
<<<<<<< HEAD
  tagline: 'Nine Realms. One Tree. Infinite Possibilities.',
  favicon: 'img/favicon.svg',

=======
  tagline: 'Forged in the Nine Realms — A project ecosystem rooted in Norse mythology',
  favicon: 'img/favicon.svg',

  future: {
    v4: true,
  },

>>>>>>> origin/main
  url: 'https://docs.brierstudios.com',
  baseUrl: '/',

  organizationName: 'BrierAinz',
  projectName: 'Yggdrasil',

  onBrokenLinks: 'throw',
<<<<<<< HEAD
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'es'],
    localeConfigs: {
      en: { htmlLang: 'en-US' },
      es: { htmlLang: 'es-ES' },
    },
=======

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
>>>>>>> origin/main
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
<<<<<<< HEAD
          editUrl: 'https://github.com/BrierAinz/Yggdrasil/tree/master/website-v2/',
=======
          editUrl: 'https://github.com/BrierAinz/Yggdrasil/tree/main/website-v2/',
>>>>>>> origin/main
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
<<<<<<< HEAD
      navbar: {
        title: 'YGGDRASIL',
        logo: {
          alt: 'Yggdrasil Logo',
          src: 'img/logo.svg',
=======
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: '᛭ Yggdrasil',
        logo: {
          alt: 'Yggdrasil Logo',
          src: 'img/logo-yggdrasil.svg',
>>>>>>> origin/main
        },
        items: [
          {
            type: 'docSidebar',
<<<<<<< HEAD
            sidebarId: 'docsSidebar',
=======
            sidebarId: 'docs',
>>>>>>> origin/main
            position: 'left',
            label: 'Docs',
          },
          {
            href: 'https://github.com/BrierAinz/Yggdrasil',
            label: 'GitHub',
            position: 'right',
          },
<<<<<<< HEAD
          {
            type: 'localeDropdown',
            position: 'right',
          },
=======
>>>>>>> origin/main
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
<<<<<<< HEAD
              { label: 'Overview', to: '/docs/intro' },
              { label: 'Architecture', to: '/docs/architecture' },
              { label: 'Setup', to: '/docs/setup' },
=======
              {label: 'Overview', to: '/docs/intro'},
              {label: 'Architecture', to: '/docs/architecture'},
              {label: 'Setup', to: '/docs/setup'},
>>>>>>> origin/main
            ],
          },
          {
            title: 'Agents',
            items: [
<<<<<<< HEAD
              { label: 'Lilith', to: '/docs/lilith' },
              { label: 'Changelog', to: '/docs/changelog' },
=======
              {label: 'Lilith', to: '/docs/lilith'},
              {label: 'Changelog', to: '/docs/changelog'},
>>>>>>> origin/main
            ],
          },
          {
            title: 'More',
            items: [
<<<<<<< HEAD
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
=======
              {label: 'GitHub', href: 'https://github.com/BrierAinz/Yggdrasil'},
            ],
          },
        ],
        copyright: `ᛒ Forged with runes and code. ${new Date().getFullYear()}`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['python', 'bash', 'yaml', 'ini'],
      },
      announcementBar: {
        id: 'yggdrasil-v5',
        content: '᛭ Yggdrasil v5 — Lilith reforged into modular packages',
        backgroundColor: '#1a1b26',
        textColor: '#c8a23e',
>>>>>>> origin/main
        isCloseable: true,
      },
    }),
};

<<<<<<< HEAD
module.exports = config;
=======
export default config;
>>>>>>> origin/main
