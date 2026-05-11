---
name: cloudflare
category: devops
description: Manage Cloudflare domains, DNS, API tokens, Pages deployment, Workers, KV, security headers, and site infrastructure. Domain registration, DNS configuration, Pages static hosting, Workers serverless functions, security hardening (CSP, HSTS, CORS), transform rules, redirects, and custom 404 pages.
triggers:
  - buy/purchase domain
  - register domain
  - Cloudflare DNS
  - configure DNS records
  - Cloudflare API token
  - point domain to
  - Cloudflare security headers
  - Cloudflare HSTS CSP
  - hardening site security
  - Cloudflare Transform Rules
  - Cloudflare redirect rules
  - deploy static site to Cloudflare Pages
  - wrangler pages deploy
  - Cloudflare Worker
  - serverless function Cloudflare
  - contact form Worker
  - Cloudflare KV
  - Cloudflare Pages _headers _redirects
  - 404 page Cloudflare Pages
---

# Cloudflare Domain & DNS Management

## Domain Registration Recommendations

When buying a .com domain, prefer these registrars (best to worst):

| Registrar | .com Price | Renewal | WHOIS Privacy | Notes |
|-----------|-----------|---------|---------------|-------|
| **Cloudflare** | ~$9.77/yr | ~$9.77 | Free | At-cost pricing, no markup. Best choice. |
| **Porkbun** | ~$9.73/yr | ~$10.67 | Free | Clean UI, good alternative. |
| **Namecheap** | ~$5.98/yr | ~$13+ | 1st yr free | Cheap entry, expensive renewal. |
| GoDaddy | ~$3/yr | $20+ | Paid | Avoid — aggressive upsells, expensive. |

**Cloudflare** and **Porkbun** are the top picks: transparent pricing, free WHOIS privacy, no upsell pressure.

### Buying on Cloudflare
- Domain purchases happen via the **web dashboard only** (dash.cloudflare.com), NOT via API.
- Go to: Domain Registration → Register Domains → search and buy.
- After purchase, the zone is automatically added to your account.

## API Token Setup

### Required Permissions
Create a token at https://dash.cloudflare.com/profile/api-tokens with:

| Permission | Resource |
|---|---|
| Zone → DNS → Edit | All zones | DNS record management |
| Zone → Zone → Read | All zones | Zone listing and info |
| Account → Cloudflare Pages → Edit | Specific account | Deploy static sites, manage custom domains |

If registering domains via API (not currently possible — web only), you'd also need:
| Account → Domain Registration → Edit | Specific account |

### Pitfall: Client IP Address Filtering
When creating a token, the "Client IP Address Filtering" section may show an empty row and refuse to proceed without a value ("Enter valid IP addresses").

**Solution**: Enter `0.0.0.0/0` — this means "all IPs" and is equivalent to no restriction. Delete the row if possible, but `0.0.0.0/0` always works as a fallback.

### Two Token Types — Critical Pitfall

Cloudflare has **two types** of API tokens that authenticate differently:

| Token Type | Prefix | Auth Endpoint | Scope |
|------------|--------|---------------|-------|
| **User Token** | `cfut_` | `/client/v4/user/tokens/verify` | Zone-level (DNS, Settings, Rules) |
| **Account Token** | `cfat_` | `/client/v4/accounts/{account_id}/...` | Full account (Pages, Rulesets, Redirects, everything) |

**Pitfall**: Account tokens (`cfat_`) return `"Invalid API Token"` at `/user/tokens/verify`. They ONLY authenticate via `/accounts/` endpoints. To verify an account token:

```bash
# This WORKS for user tokens (cfut_):
curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer cfut_xxx..."

# This WORKS for account tokens (cfat_):
curl -s "https://api.cloudflare.com/client/v4/accounts/{account_id}" \
  -H "Authorization: Bearer cfat_xxx..."
```

**Pitfall**: If you get `"Invalid API Token"` with a known-good token, check the prefix. Account tokens cannot be verified at the user endpoint and vice versa.

**Tip**: For full control (Pages, Bulk Redirects, Transform Rules, DNS, everything), prefer Account tokens. User tokens are limited to zone-level operations.

### Token Verification
```bash
# User token (cfut_*) verification
curl -s -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"
# Look for: "status": "active"

# Account token (cfat_*) verification — use /accounts/ endpoint
curl -s "https://api.cloudflare.com/client/v4/accounts/{account_id}" \
  -H "Authorization: Bearer <TOKEN>"
# Look for: "success": true
```

### Listing Zones
```bash
curl -s -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"
```

## DNS Configuration

### Pointing to GitHub Pages
For a domain pointing to GitHub Pages (e.g., brierainz.github.io):

1. Add the domain as a custom domain in the GitHub repo Settings → Pages.
2. In Cloudflare DNS, create these records:
   - **CNAME**: `@` → `<username>.github.io` (apex domain)
   - **CNAME**: `www` → `<username>.github.io`
3. Wait for GitHub to provision the SSL certificate (can take minutes).
4. Cloudflare proxy (orange cloud) recommended for free SSL/DDoS protection.

### Common DNS Records
| Type | Name | Value | Use Case |
|------|------|-------|----------|
| A | @ | 185.199.108-111.153 | GitHub Pages apex |
| CNAME | www | username.github.io | GitHub Pages www |
| CNAME | sub | target.domain.com | Subdomain |
| TXT | @ | verification value | Domain verification |
| MX | @ | mail server | Email |

## Cloudflare Pages Deployment

For static sites (landing pages, SPAs, docs), Cloudflare Pages is the best deployment option when the domain is already on Cloudflare.

### Token Requirements for Pages

The DNS-only token (Zone:DNS:Edit + Zone:Zone:Read) is **NOT sufficient** for Pages deployment. You also need:

| Permission | Resource | Purpose |
|---|---|---|
| Account → Cloudflare Pages → Edit | Specific account | Create projects, deploy, manage custom domains |

Without this, you get: `Authentication error [code: 10000]` on `/accounts/{id}/pages/projects`.

### Deploy via CLI (wrangler) — Non-interactive with API Token

This is the preferred method for automated/hermes-driven deploys (no browser login needed):

```bash
# Set env vars (token and account ID are required for non-interactive)
export CLOUDFLARE_API_TOKEN="cfut_xxx..."
export CLOUDFLARE_ACCOUNT_ID="your_account_id"

# Create project first (one-time)
npx wrangler@latest pages project create <project-name> --production-branch=main

# Deploy a local directory
npx wrangler@latest pages deploy ./site-directory --project-name=<project-name> --branch=main

# For dirty git repos, add --commit-dirty=true to suppress warning
```

**Pitfall**: Without `CLOUDFLARE_ACCOUNT_ID`, wrangler fails with "Failed to automatically retrieve account IDs". Always set both env vars.

**Pitfall**: The `wrangler login` flow is for interactive use only. For API-driven deploys, always use `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` env vars.

### Deploy via Git (auto-deploy from GitHub)
1. Go to dash.cloudflare.com → Workers & Pages → Create → Pages → Connect to Git
2. Connect GitHub repo → select branch
3. Set build command (leave empty for static HTML) and output directory (`/` or `.`)
4. Deploy — each push to the branch auto-deploys

### Custom Domain on Pages via API

After project creation, add custom domains programmatically:

```bash
# Add custom domain to Pages project
curl -s -X POST \
  "https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/{project_name}/domains" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"example.com"}'

# Add DNS CNAME record pointing to pages.dev
curl -s -X POST \
  "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"example.com","content":"example.pages.dev","proxied":true}'

# Add www subdomain too
curl -s -X POST \
  "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"www","content":"example.pages.dev","proxied":true}'
```

Cloudflare auto-provisions SSL when domain is proxied (orange cloud). Domain activation status goes from `initializing` → `active` within minutes.

### Pitfall: Workers vs Pages Confusion

The Cloudflare dashboard "Create application" flow defaults to **Workers** setup (with `npx wrangler deploy` command). For static sites (HTML/CSS/JS), you want **Pages**, not Workers. Workers are for serverless functions; Pages are for static sites with automatic Git integration and preview deployments.

When using the dashboard: choose **Workers & Pages → Create → Pages** (not Workers). When using CLI: use `wrangler pages deploy`, not `wrangler deploy`.

### Pitfall: Apex domain redirect
For `www` → `apex` redirect, Cloudflare handles this automatically when both are added as custom domains in Pages. Alternatively, add a Page Rule or Bulk Redirect.

## Security Headers via Rulesets API

### Adding Security Headers (Transform Rules)

Use the Rulesets API to add security headers (CSP, HSTS, X-Frame-Options, etc.) via `http_response_headers_transform` phase:

```bash
# Create/update transform rule for security headers
curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets/phases/http_response_headers_transform/entrypoint" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Security Headers",
    "description": "Add security headers and remove CORS wildcard",
    "rules": [
      {
        "expression": "http.host eq \"example.com\" or http.host eq \"www.example.com\"",
        "description": "Add security headers",
        "enabled": true,
        "action": "rewrite",
        "action_parameters": {
          "headers": {
            "Content-Security-Policy": {
              "operation": "set",
              "value": "default-src '\''self'\''; script-src '\''self'\'' static.cloudflareinsights.com; style-src '\''self'\'' fonts.googleapis.com '\''unsafe-inline'\''; font-src fonts.gstatic.com; img-src '\''self'\'' data:; connect-src '\''self'\''"
            },
            "X-Frame-Options": {
              "operation": "set",
              "value": "DENY"
            },
            "Permissions-Policy": {
              "operation": "set",
              "value": "camera=(), microphone=(), geolocation=()"
            },
            "Access-Control-Allow-Origin": {
              "operation": "remove"
            }
          }
        }
      }
    ]
  }'
```

### Pitfalls

1. **Phase name is `http_response_headers_transform`**, NOT `http_response_transform`. The shorter name returns `"unknown phase"` error.

2. **Header removal** uses `"operation": "remove"` with no `value` field. This removes headers like `Access-Control-Allow-Origin: *`.

3. **`http_request_redirect` is NOT allowed at zone level.** It returns `"phase not allowed at zone level"`. For redirects, either:
   - Add both apex and www as Pages custom domains (Cloudflare auto-redirects www→apex)
   - Use Cloudflare dashboard → Rules → Redirect Rules (requires Account-level permissions)
   - Use Bulk Redirects via Account API (requires Account→Rules→Edit permission)

6. **Bulk Redirects API** requires account-level permissions and uses a specific JSON format. Create a redirect list first, then add items as a raw JSON array (NOT wrapped in an object):

```bash
# Step 1: Create redirect list
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/rules/lists" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"www_to_apex","description":"Redirect www to apex","kind":"redirect"}'

# Step 2: Add items — MUST be a raw JSON array, NOT a JSON object with "items" key
curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/rules/lists/$LIST_ID/items" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"redirect":{"source_url":"www.example.com/*","target_url":"https://example.com/$1","status_code":301}}]'

# Pitfall: Wrapping in {"items": [...]} causes "filters.api.invalid_json" error.
# The body MUST be the array directly: [item1, item2, ...]

# Step 3: Create zone ruleset referencing the list (requires free-plan compatible phase)
# http_request_redirect phase is NOT available at zone level on Free plans.
# However, if both apex and www are Pages custom domains, Cloudflare auto-serves both.
```

7. **Pages custom domains auto-redirect**: When both `example.com` and `www.example.com` are added as custom domains on a Cloudflare Pages project, they both serve the site. No redirect rules needed.

4. **Expression must match ALL hostnames** where headers should apply. A rule with `http.host eq "example.com"` will NOT apply to `www.example.com`. Use `http.host eq "example.com" or http.host eq "www.example.com"`.

5. **HSTS** is configured separately in the Cloudflare dashboard under SSL/TLS → Edge Certificates → HSTS (not via Rulesets API). Enable with max-age=31536000, includeSubDomains, preload. After enabling HSTS, submit to https://hstspreload.org/ for browser-level preloading (one-time manual step, takes weeks to propagate).

6. **Token permissions for Transform/Redirect Rules** need Zone → Rules → Edit on the target zone. The DNS+Pages token is NOT sufficient.

### Recommended Security Headers

| Header | Value | Priority |
|--------|-------|----------|
| Content-Security-Policy | `default-src 'self'; script-src 'self' static.cloudflareinsights.com; ...` | CRITICAL |
| Strict-Transport-Security | `max-age=31536000; includeSubDomains; preload` (via dashboard) | CRITICAL |
| X-Frame-Options | `DENY` | HIGH |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` | MEDIUM |
| Access-Control-Allow-Origin | REMOVE if `*` (via `"operation": "remove"`) | HIGH |

### Verification

```bash
# Check headers on both apex and www
curl -sI https://example.com | grep -iE "strict-transport|content-security|x-frame|permissions-policy|access-control"
curl -sI https://www.example.com | grep -iE "strict-transport|content-security|x-frame|permissions-policy|access-control"
```

## Cloudflare Pages Static Files (`_headers`, `_redirects`, `404.html`)

For Pages projects, you can place special routing/headers files in the deployment root instead of (or in addition to) API-based Transform Rules. These are simpler and more maintainable for static sites.

### `_headers` File

Create a `_headers` file in your deploy directory. Cloudflare Pages processes it automatically:

```
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self' static.cloudflareinsights.com; style-src 'self' fonts.googleapis.com 'unsafe-inline'; font-src fonts.gstatic.com; img-src 'self' data:; connect-src 'self'

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/*.css
  Cache-Control: public, max-age=3153600

/*.js
  Cache-Control: public, max-age=3153600
```

**Pitfall**: The `_headers` file uses path patterns (not expressions). `/*` matches all paths. Headers from `_headers` are additive with Transform Rules — both are applied. If there's a conflict, the more specific path wins.

**Pitfall**: Each header block must have a blank line between path pattern and the next block. Indentation matters — headers must be indented under their path.

### `_redirects` File

```
/www.brierstudios.com/* https://brierstudios.com/:splat 301
```

**Pitfall**: The `_redirects` file only works when the Pages project has the domain as a custom domain. It does NOT replace Transform Rules or redirect rules for non-Pages traffic.

### Custom 404 Page

Place a `404.html` in your deploy directory. Cloudflare Pages serves it automatically for any path that doesn't match a file.

## Cloudflare Workers Deployment

### Worker + KV Namespace

For form handlers, API endpoints, or serverless functions alongside a Pages site:

```bash
# 1. Create KV namespace
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/storage/kv/namespaces" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"project-name-contacts"}'
# Response includes: "id": "abc123..."

# 2. Create wrangler.toml
cat > wrangler.toml << 'EOF'
name = "project-contact"
main = "worker-contact.js"
compatibility_date = "2024-12-01"

[vars]
ENVIRONMENT = "production"

[[kv_namespaces]]
binding = "CONTACTS"
id = "abc123..."  # From step 1
EOF

# 3. Deploy
export CLOUDFLARE_API_TOKEN="$TOKEN"
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"
npx wrangler deploy
```

**Pitfall**: The KV namespace `id` in `wrangler.toml` must be the **namespace ID** (hex string), NOT the binding name. Mismatch causes `kv.get is not a function` at runtime.

**Pitfall**: `wrangler deploy` (no `pages`) deploys a Worker, not a Pages site. Use `wrangler pages deploy` for static sites.

### Worker Custom Domain

To serve a Worker on a custom subdomain (e.g., `contact.brierstudios.com`), use the **Workers Domains API** (preferred) or **wrangler.toml routes**.

#### Option A: Workers Domains API (Recommended)

This is the cleanest approach — Cloudflare automatically manages DNS and routing:

```bash
# Step 1: Deploy the Worker first
export CLOUDFLARE_API_TOKEN="$TOKEN"
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"
npx wrangler deploy

# Step 2: Add custom domain via Workers Domains API
curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/workers/domains" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "contact.example.com",
    "zone_id": "'$ZONE_ID'",
    "service": "project-contact",
    "environment": "production"
  }'
# Response includes: {"success": true, "result": {"hostname": "contact.example.com", "enabled": true, ...}}
```

**CRITICAL Pitfall**: If a DNS record (CNAME/A/AAAA) already exists for the hostname, the API returns error 100117: `"Hostname already has externally managed DNS records"`. You MUST delete the existing DNS record first:

```bash
# Find and delete existing record
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=contact.example.com" \
  -H "Authorization: Bearer $TOKEN"
# Then delete it:
curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
  -H "Authorization: Bearer $TOKEN"
# Now retry the Workers Domains API call
```

**Pitfall**: Do NOT manually create a CNAME pointing to the Worker's `workers.dev` subdomain and then try to add a Workers Domain — they conflict. The Workers Domains API creates its own managed DNS record automatically.

#### Option B: Wrangler.toml Routes

```toml
[[routes]]
pattern = "contact.example.com/*"
zone_name = "example.com"
```

This requires the zone to already have DNS pointing to Cloudflare.

#### Option C: Manual DNS CNAME (Not Recommended)

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"contact","content":"project-name.account.workers.dev","proxied":true}'
```

This gives a 522 error because the CNAME doesn't route to the Worker. Use Option A instead.

### Worker CORS Pattern

For Workers receiving requests from a Pages site:

```javascript
export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': 'https://example.com',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }
    // ... handle POST
    return new Response(JSON.stringify({success: true}), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': 'https://example.com',
      },
    });
  },
};
```

**Pitfall**: Never set `Access-Control-Allow-Origin: *` for form handlers. Scope it to the exact origin.

### Full Site Enhancement Checklist (Direct Upload)

When enhancing an existing Cloudflare Pages site (direct upload mode, no Git integration):

1. Clone the repo: `gh repo clone <user>/<repo>`
2. Make changes locally
3. `git add -A && git commit && git push` (version control)
4. Deploy: `npx wrangler pages deploy . --project-name=<name>` (env vars required for non-interactive)
5. If Worker changes: `npx wrangler deploy` in the Worker directory
6. Verify: `browser_navigate` to check, `browser_console` for JS errors, `curl -sI` for headers

**Pitfall**: For direct-upload projects, pushing to GitHub does NOT auto-deploy. You must run `wrangler pages deploy` manually each time. Only Git-connected projects auto-deploy on push.

**Pitfall**: The `--project-name` must match the EXACT Pages project name (check with `wrangler pages project list`). A wrong name returns error 8000007 "Project not found". E.g., the project is `brierstudios`, NOT `brierstudios-site`.

**Pitfall**: Running `wrangler pages deploy` without `CLOUDFLARE_API_TOKEN` env var fails with "non-interactive environment" error. Always set it: `CLOUDFLARE_API_TOKEN=cfat_... npx wrangler pages deploy . --project-name=xxx`

**CRITICAL Pitfall — Wrangler content-hash caching**: Wrangler hashes each file and skips upload if the hash matches a previously deployed version. But after modifying CSS/JS, Cloudflare's CDN serves the cached old version. Symptoms: deploy says "0 files uploaded" but changes aren't visible on the live site.

Two-step fix:
1. **Cache-bust URLs in HTML**: Add `?v=X.Y` to all `<link>` and `<script>` src/href URLs pointing to your own assets. This forces browsers and CDN edge nodes to fetch the new version.
   ```html
   <link rel="stylesheet" href="styles.css?v=2.1">
   <script src="script.js?v=2.1" defer></script>
   ```
2. **Force wrangler to re-upload changed files**: If wrangler still says "0 files uploaded" after you changed a file, append a trivial comment to force a different hash: `echo "/* v2.1 */" >> styles.css`. Alternatively, delete `.wrangler/` local cache before deploying: `rm -rf .wrangler && npx wrangler pages deploy .`

**Pitfall — Account tokens cannot purge CDN cache**: Account tokens (`cfat_*`) return auth error 10000 on `POST /zones/{id}/purge_cache`. You cannot purge Cloudflare's CDN cache programmatically with account tokens. Instead, use cache-busting query parameters (`?v=X`) in your HTML. This is more reliable anyway since it busts both CDN and browser caches.

### SRI (Subresource Integrity) for External Resources

For Google Fonts and other CDN resources, add `integrity` and `crossorigin` attributes:

```html
<link href="https://fonts.googleapis.com/css2?family=..." rel="stylesheet"
      integrity="sha256-HASH_HERE=" crossorigin>
```

**Pitfall**: Google Fonts CSS is user-agent-dependent (serves different WOFF2 subsets per UA). The SRI hash computed from one UA may not match another. For maximum compat, either self-host the font files or accept that some UAs may fail SRI checks and fall back gracefully.

**Generating SRI hashes**:
```bash
# For a CSS/JS file
curl -s URL | openssl dgst -sha256 -binary | openssl base64 -A
# Result: "sha256-XXXXX="
```

### SEO + LLM Discovery for Static Sites

When deploying a static site (landing page, Docusaurus docs, etc.) to Cloudflare Pages, add these files for discoverability:

1. **`llms.txt`** — Plain text at root describing your brand/products for AI crawlers (ChatGPT, Claude, Perplexity). Format: Markdown text with `##` sections for What, Products, Tech Stack, Links.
2. **`sitemap.xml`** — List all public URLs with `<lastmod>`, `<changefreq>`, `<priority>`. Include both main site and docs subdomain URLs.
3. **`robots.txt`** — Allow all crawlers + explicit allows for LLM bots (GPTBot, ChatGPT-User, CCBot, Google-Extended, OAI-SearchBot, PerplexityBot). Disallow `/assets/` (images/fonts used internally).
4. **`<meta>` tags** — Every HTML page should have: description, keywords, author, robots (index,follow), plus OG + Twitter Card + Schema.org JSON-LD with matching descriptions.
5. **Cache-bust** — After any HTML/CSS/JS change, bump `?v=X.Y` query params on all `<link>` and `<script>` tags. Account tokens (`cfat_*`) cannot purge CDN cache via API.

### Social Links Integration

For any site (landing or Docusaurus docs), add social media links consistently:

**Landing site (vanilla HTML):**
- Contact section: add items with runas as icons (e.g. ᛉ for Twitter/X, ᛁ for Instagram)
- Footer: add a `.footer-links` row with emoji/text links (𝕏, 📷, ⌘, 📖), styled with hover glow (cyan/magenta)
- Update `llms.txt` Contact section with all social URLs
- Update Schema.org JSON-LD `sameAs` array with social profile URLs

**Docusaurus docs:**
- Navbar: add `{href: 'https://x.com/...', label: '𝕏', position: 'right'}` items for each social link (emoji labels are compact and don't need SVGs)
- Footer: add social links under "Community" section, add "Main Site" link under "More" section (avoids duplicating GitHub)
- Docusaurus emoji navbar labels work well — no icon font or SVG needed

### PWA for Static Sites on Cloudflare Pages

For a PWA, you need three files:
1. `manifest.json` — app name, icons, theme colors, display mode
2. `sw.js` — service worker (cache-first for assets, network-first for HTML)
3. Registration in HTML: `<link rel="manifest" href="/manifest.json">` + JS `navigator.serviceWorker.register('/sw.js')`

**Pitfall**: The service worker scope must be `/` (place `sw.js` in deploy root). Service workers only control pages at or below their scope.

### CSP Enforcement via `_headers`

Cloudflare Pages `_headers` file supports full CSP directives. Use enforcing mode (NOT `Content-Security-Policy-Report-Only`):

```
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://contact.example.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://contact.example.com
```

**Tip**: Include `static.cloudflareinsights.com` in `script-src` if using Cloudflare Web Analytics. Include your Worker domain in `connect-src` and `form-action` if forms POST there.

## Linked References

- `references/brierstudios-deployment.md` — BrierStudios site: Cloudflare Pages deploy, frost dark fantasy design specs, DNS configuration, logo remastering
- `references/brierstudios-security.md` — Security hardening: Transform Rules, HSTS, CSP, header removal, API commands, verification
- `references/brierstudios-enhancement.md` — Full site enhancement: SEO, aurora effects, contact Worker+KV, 404 page, deploy commands
- `templates/worker-contact.js` — Reusable Cloudflare Worker template for contact forms (KV-backed, CORS-scoped, validated)
- `templates/_headers` — Reusable Cloudflare Pages `_headers` template with security headers + cache rules

## Cheatsheet

- **Account ID**: `${CLOUDFLARE_ACCOUNT_ID}`
- **Zone ID** (brierstudios.com): `${CLOUDFLARE_ZONE_ID}`
- **Account Token** (`cfat_*`): full admin, authenticates via `/accounts/{id}` endpoints
- **User Token** (`cfut_*`): zone-limited (DNS Edit, Zone Read, Pages Edit), authenticates via `/user/tokens/verify`
- **Pages project name**: `brierstudios` (NOT `brierstudios-site`)
- **Landing version**: v2.7 (a11y: skip-link, aria-expanded, focus-visible ring, viewport-fit=cover; SEO: Schema.org enriched, contrast improved; CSP hardened with object-src 'none'; canvas pause on tab hidden)
- **Docs project name**: `docs-brierstudios` (Docusaurus v3, custom domain `docs.brierstudios.com`)
- **Docs project path**: `/home/brierainz/comfy/docs-brierstudios/` (build: `npm run build`, deploy: `wrangler pages deploy build --project-name=docs-brierstudios`)
- Domain purchases: web dashboard only
- DNS changes: API supported
- Cloudflare Pages: preferred deployment for static sites on CF domains
- Security headers: via `http_response_headers_transform` ruleset phase OR `_headers` file
- Always verify token before performing operations (use correct endpoint for token type)
- Deploy command: `CLOUDFLARE_API_TOKEN=cfat_xxx npx wrangler pages deploy . --project-name=brierstudios`