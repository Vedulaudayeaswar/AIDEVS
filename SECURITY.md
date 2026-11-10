# Security Policy

## Reporting a vulnerability
Please **do not open a public issue** for security problems. Use GitHub's
[private vulnerability reporting](https://github.com/Vedulaudayeaswar/AIDevs/security/advisories/new)
or email [security contact email]. Include steps to reproduce, affected versions and impact.
We aim to acknowledge reports within 3 business days.

## Supported versions
Only the latest `main` branch receives security fixes.

## Security model (summary)
- **Secrets:** one platform `GROQ_API_KEY`, server-side only; never sent to browsers, never in exports.
  `.env` files are git-ignored everywhere; CI runs gitleaks and fails if a secret-like string reaches the frontend bundle.
- **Auth:** bcrypt (cost 12); 15-minute access JWTs; rotating, hashed, revocable refresh tokens with reuse detection;
  logout and password change revoke sessions; login/register rate limiting that cannot be bypassed with `X-Forwarded-For`.
- **Authorization:** every project-scoped route resolves ownership on the server (`get_owned_project`) and answers 404
  for other users' data. Admin routes re-check the role server-side.
- **Generated code:** the platform never executes generated application code on the server. Previews run in a
  sandboxed iframe (`sandbox="allow-scripts"`, opaque origin, CSP `connect-src 'none'`), content is schema-sanitized,
  and the only script is the platform's nonce'd editor bridge. Generated backends are produced by a deterministic
  compiler; the Testing agent only syntax-compiles them (`compile()`), it does not run them. See `docs/ARCHITECTURE.md`.
- **SSRF:** the reference-site crawler only allows public IPs on ports 80/443, pins the connection to the vetted
  address, re-validates every redirect and honours robots.txt.
- **Uploads:** Pillow-verified PNG/JPEG/GIF/WebP only (no SVG), size and per-user storage limits.

## Hardening checklist for operators
- Set a strong `JWT_SECRET_KEY` (Render generates one) and restrict `CORS_ORIGINS` to your site.
- Keep `TRUST_PROXY_HOPS` equal to the number of proxies in front of the API (1 on Render).
- Set `ADMIN_EMAILS` only to accounts you control; use `REGISTRATION_OPEN=0` to pause sign-ups.
- Enable GitHub secret scanning + push protection and Dependabot alerts on the repository.
- Rotate the Groq key if it was ever shared, logged or committed anywhere.
