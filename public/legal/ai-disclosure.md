# AI-Generated Content Disclosure

> DRAFT — requires legal review before public launch.

- AIDevs uses large language models served by **Groq** (currently from the open-weight GPT-OSS family; the exact model per task is configured by the operator) to write project specifications, page designs, copy and change plans.
- Backend code, database models, API endpoints and tests in exported projects are **generated deterministically** from your data models by AIDevs' own compiler, not written free-form by the AI.
- AI output can be wrong, incomplete, biased, insecure or similar to existing works. Placeholder images come from public placeholder services. **Review, test and secure** your project before publishing it, and check that text, images and branding are yours to use.
- Automated checks (contract, accessibility, SEO, responsive, permission and compile checks) reduce, but do not eliminate, defects. They are not a security audit.
- If you publish a site built with AIDevs, consider disclosing that parts of it were AI-assisted where your jurisdiction or audience expects it.
