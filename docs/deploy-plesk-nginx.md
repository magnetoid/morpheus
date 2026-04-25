# Plesk → Coolify Traefik reverse proxy

Use this when your Plesk-managed server already terminates TLS on
`yourdomain.com` and you want Plesk's Nginx to forward requests to a
Coolify-managed Morpheus stack running behind Traefik on the **same** host
(or a different one).

---

## Topology

```
        ┌─────────┐  HTTPS  ┌──────────────────┐  HTTP  ┌──────────────────────┐
client →│ Plesk   │ ──────→ │ Plesk Nginx      │ ─────→ │ Coolify Traefik      │ → Morpheus
        │ (TLS)   │         │ (reverse proxy)  │        │ (port 80, internal)  │
        └─────────┘         └──────────────────┘        └──────────────────────┘
```

Two TLS termination strategies — pick **one**:

| Strategy | TLS terminated by | Coolify needs | Notes |
|---|---|---|---|
| A. Plesk-only | Plesk | nothing extra | Simplest. Coolify Traefik serves plain HTTP on port 80, only reachable via Plesk. |
| B. Plesk + Coolify | Plesk fronts; Coolify also has a cert | Coolify domain config | Stronger isolation. Plesk → HTTPS to Coolify. |

The configs below cover **strategy A** (most common). For B, add `proxy_pass https://...` and `proxy_ssl_server_name on`.

---

## Plesk Nginx config

In Plesk, open the domain → **Apache & nginx Settings** →
**Additional nginx directives** and paste the snippet below. Replace
`yourdomain.com` with your actual domain and `127.0.0.1` with your
Coolify host's IP if it's a different machine.

```nginx
# Morpheus (via Coolify Traefik)
# Plesk terminates TLS; Coolify Traefik runs on :80 inside the host network.
location / {
    # Buffering off so SSE / agent streaming responses are not chunked.
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_redirect off;

    # Pass through to Coolify Traefik on the host.
    proxy_pass http://127.0.0.1:80;

    # Required so Traefik's host-based routing matches.
    proxy_set_header Host              $host;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Request-ID      $request_id;

    # WebSocket / HTTP/2 upgrade for the GraphQL playground + future SSE.
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection $connection_upgrade;

    # Sensible timeouts. Tune for your workload — agent SSE may need 600s+.
    proxy_connect_timeout   30s;
    proxy_send_timeout      120s;
    proxy_read_timeout      120s;
    send_timeout            120s;
}

# Coolify Traefik dashboard (optional — gate on IP).
# location = /traefik {
#     allow 1.2.3.4;
#     deny all;
#     proxy_pass http://127.0.0.1:8080/dashboard/;
# }

# Larger uploads (admin product imports, photo uploads).
client_max_body_size 50m;
```

The `$connection_upgrade` variable needs to be defined in `nginx.conf`
(Plesk usually has it). If you get a `nginx: $connection_upgrade is not
defined` error, add this to **Custom directives** at the http level (or
ask Plesk support to add it):

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

---

## On the Coolify side

In Coolify, when you create the Morpheus application (Docker Compose →
`magnetoid/morpheus` repo, default `docker-compose.yml`):

1. **Domains:** bind the same `yourdomain.com` to the `web` service.
   Coolify will provision a Let's Encrypt cert. With strategy A above
   the cert is unused (Plesk terminates), but it doesn't hurt.

2. **Required env vars (in Coolify's panel):**

   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | random 64-char string |
   | `ALLOWED_HOSTS` | `yourdomain.com` |
   | `CORS_ALLOWED_ORIGINS` | `https://yourdomain.com` |
   | `STRIPE_SECRET_KEY` | from Stripe |
   | `OPENAI_API_KEY` | from OpenAI |

   `SERVICE_FQDN_WEB`, `SERVICE_PASSWORD_POSTGRES`, `SERVICE_PASSWORD_REDIS`
   are **auto-injected** by Coolify — do not set them yourself.

3. Hit **Deploy**.

4. Once green, in Coolify's terminal for the `web` container:
   ```bash
   python manage.py morph_seed_demo        # 25 books, 6 categories, 1 paid order
   python manage.py createsuperuser
   ```

---

## Verifying the chain

```bash
# Plesk terminus
curl -I https://yourdomain.com/healthz
# → HTTP/2 200, content-type: application/json

# Coolify Traefik terminus (from the host, internal)
curl -I http://127.0.0.1/healthz -H "Host: yourdomain.com"
# → HTTP/1.1 200, X-Request-ID: <hex>

# Sanity-check storefront pages
curl -sSL https://yourdomain.com/                    | grep -o '<title>.*</title>'
curl -sSL https://yourdomain.com/products/           | head -5
curl -sSL https://yourdomain.com/sitemap.xml         | head -3
```

If `/healthz` works through Plesk but pages 404, check the
`Host` header propagation — Traefik routes by `Host()` rule and silently
404s on unknown hosts.

---

## Common issues

**`502 Bad Gateway` from Plesk**
Coolify Traefik is not running on `127.0.0.1:80`. Check `docker ps |
grep coolify-proxy` on the host.

**`502 Bad Gateway` from Traefik**
The Morpheus `web` container is not healthy. Coolify dashboard → app →
**Logs**.

**Pages render but `/sitemap.xml` is empty**
SEO plugin works, but the catalog has no rows yet. Run
`python manage.py morph_seed_demo`.

**Browser shows TLS warning**
Strategy A: Plesk's cert covers `yourdomain.com` but the request is
hitting Coolify Traefik directly (not through Plesk). Confirm DNS points
at the Plesk IP.

**Logged-in admin redirects in a loop**
Django doesn't know it's behind a TLS terminator. Make sure
`X-Forwarded-Proto https` is being passed (it is, in the snippet above)
and `SECURE_PROXY_SSL_HEADER` is set on the Django side. Add to env:
`SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https`

---

## Multiple Morpheus stacks behind one Plesk

If you run multiple Morpheus stacks behind Plesk (e.g. dot books +
another tenant), give each its own domain in Plesk and let
Coolify/Traefik route by `Host` — the same Nginx block works unchanged
for each subdomain because it forwards `$host`.
