// @ts-check
import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Yggdrasil',
  tagline: 'A personal project ecosystem rooted in Norse mythology',
  favicon: 'img/favicon.svg',

  future: {
    v4: true,
  },

  url: 'https://brierainz.github.io',
  baseUrl: '/Yggdrasil/',

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
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/BrierAinz/Yggdrasil/tree/main/website-v2/',
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
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Yggdrasil',
        logo: {
          alt: 'Yggdrasil Logo',
          src: 'img/logo-yggdrasil.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docs',
            position: 'left',
            label: 'Docs',
          },
          {
            href: 'https://github.com/BrierAinz/Yggdrasil',
            label: 'GitHub',
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
              {label: 'Overview', to: '/docs/intro'},
              {label: 'Architecture', to: '/docs/architecture'},
              {label: 'Setup', to: '/docs/setup'},
            ],
          },
          {
            title: 'Agents',
            items: [
              {label: 'Lilith', to: '/docs/lilith'},
              {label: 'Changelog', to: '/docs/changelog'},
            ],
          },
          {
            title: 'More',
            items: [
              {label: 'GitHub', href: 'https://github.com/BrierAinz/Yggdrasil'},
            ],
          },
        ],
        copyright: `Built with runes and code. ${new Date().getFullYear()}`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['python', 'bash', 'yaml', 'ini'],
      },
      announcementBar: {
        id: 'yggdrasil-v5',
        content: 'Yggdrasil v5 — Lilith refactored into modular packages',
        backgroundColor: '#1a1b26',
        textColor: '#c8a23e',
        isCloseable: true,
      },
    }),
};

export default config;
