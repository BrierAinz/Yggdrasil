# BrierStudios Security Hardening Reference

## Site URLs
- **Production**: https://brierstudios.com
- **Pages**: https://brierstudios.pages.dev
- **www**: https://www.brierstudios.com (serves same site, both custom domains active on Pages)

## Security Headers Applied (May 2026)

Configured via Cloudflare Transform Rules (Rulesets API, phase `http_response_headers_transform`):

| Header | Value |
|--------|-------|
| Content-Security-Policy | `default-src 'self'; script-src 'self' static.cloudflareinsights.com; style-src 'self' fonts.googleapis.com 'unsafe-inline'; font-src fonts.gstatic.com; img-src 'self' data:; connect-src 'self'` |
| X-Frame-Options | `DENY` |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` |
| Access-Control-Allow-Origin | **REMOVED** (was `*`) |

Ruleset expression: `http.host eq "brierstudios.com" or http.host eq "www.brierstudios.com"`

## HSTS

Configured via Cloudflare dashboard (SSL/TLS → Edge Certificates → HSTS):
- max-age: 31536000 (12 months)
- includeSubDomains: enabled
- preload: enabled
- No Sniff: enabled

## www → apex Redirect

NOT configured via redirect rules (Free plan doesn't support `http_request_redirect` phase at zone level, and Bulk Redirects API requires account-level ruleset creation).

Instead, both `brierstudios.com` and `www.brierstudios.com` are configured as custom domains on the Cloudflare Pages project `brierstudios`. Pages serves both domains correctly with the same content and security headers.

## API Commands Used

### Transform Rule creation
```bash
curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE/rulesets/phases/http_response_headers_transform/entrypoint" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Security Headers",
    "description": "Add security headers and remove CORS wildcard",
    "rules": [{
      "expression": "http.host eq \"brierstudios.com\" or http.host eq \"www.brierstudios.com\"",
      "description": "Add security headers",
      "enabled": true,
      "action": "rewrite",
      "action_parameters": {
        "headers": {
          "Content-Security-Policy": {"operation": "set", "value": "default-src 'self'; ..."},
          "X-Frame-Options": {"operation": "set", "value": "DENY"},
          "Permissions-Policy": {"operation": "set", "value": "camera=(), microphone=(), geolocation=()"},
          "Access-Control-Allow-Origin": {"operation": "remove"}
        }
      }
    }]
  }'
```

### Verification
```bash
curl -sI https://brierstudios.com | grep -iE "strict-transport|content-security|x-frame|permissions-policy|access-control"
curl -sI https://www.brierstudios.com | grep -iE "strict-transport|content-security|x-frame|permissions-policy|access-control"
```

## Remaining Recommendations

- **SRI** (Subresource Integrity): Add `integrity` attribute to `<script src="script.js">` in HTML
- **HSTS Preload**: ✅ Submitted May 2026 and accepted as pending at https://hstspreload.org/ — domain is now in the preload list queue. Takes several weeks to go live in browser Chromium releases.
- **CORS**: If API access is needed in the future, replace wildcard with specific origin allowlisting

## Security Rating

**A-** (up from B+, pending HSTS preload activation in browsers)
- Missing only: SRI on inline scripts, SRI hashes for Google Fonts