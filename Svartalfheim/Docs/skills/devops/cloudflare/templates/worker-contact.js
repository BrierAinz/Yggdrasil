/**
 * Cloudflare Worker: Contact Form Handler
 * Receives JSON form data, validates, stores in KV, returns CORS-safe response.
 *
 * Deployment:
 *   1. Create KV namespace: curl -X POST .../storage/kv/namespaces -d '{"title":"project-contacts"}'
 *   2. Copy namespace ID into wrangler.toml
 *   3. `npx wrangler deploy`
 *   4. Add DNS CNAME for custom subdomain (requires Zone:DNS:Edit permission)
 *
 * wrangler.toml:
 *   name = "project-contact"
 *   main = "worker-contact.js"
 *   compatibility_date = "2024-12-01"
 *   [[kv_namespaces]]
 *   binding = "CONTACTS"
 *   id = "<your-kv-namespace-id>"
 */

const ALLOWED_ORIGIN = 'https://example.com';  // Change to your site

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const data = await request.json();
      const { name, email, subject, message } = data;

      if (!name || !email || !message) {
        return new Response(JSON.stringify({ error: 'Name, email, and message are required.' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        return new Response(JSON.stringify({ error: 'Invalid email address.' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      const id = crypto.randomUUID();
      const entry = {
        id,
        name: String(name).slice(0, 200),
        email: String(email).slice(0, 200),
        subject: String(subject || '').slice(0, 500),
        message: String(message).slice(0, 5000),
        timestamp: new Date().toISOString(),
        ip: request.headers.get('CF-Connecting-IP') || 'unknown',
      };

      if (env.CONTACTS) {
        await env.CONTACTS.put(`contact:${id}`, JSON.stringify(entry), {
          expirationTtl: 90 * 24 * 60 * 60,  // 90 days
        });
      }

      return new Response(JSON.stringify({ success: true, id }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
        },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: 'Invalid request.' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};