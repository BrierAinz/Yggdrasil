# robots.txt for Documentation Sites

## Pattern

Every Docusaurus docs site should have a `static/robots.txt` that:

1. Allows all crawlers by default
2. Links to the sitemap
3. Explicitly allows major LLM crawlers (GPTBot, CCBot, etc.) for discoverability
4. Blocks internal paths like `/sw.js` and `/worker-`

## Template

```
# <Site> robots.txt
User-agent: *
Allow: /

# Sitemaps
Sitemap: https://docs.example.com/sitemap.xml

# LLM-friendly crawling
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: CCBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

# Block internal paths
User-agent: *
Disallow: /sw.js
Disallow: /worker-
```

## Why Explicit LLM Bot Allowance?

Some sites block AI crawlers by default. For documentation/knowledge sites, you want the opposite — maximize discoverability. The explicit `Allow` for GPTBot, CCBot, etc. ensures these bots aren't accidentally blocked by a catch-all `Disallow` rule.

## Pitfall: Don't Block `/assets/`

A previous version blocked `/assets/` which prevented image indexing (including social card images, logo). Only block paths that are truly internal (service workers, worker scripts).