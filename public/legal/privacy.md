# Privacy Policy

> DRAFT — not legal advice. Requires review by a qualified lawyer (for example GDPR, CCPA or DPDP applicability) before public launch. We do not claim any certification or formal compliance status.

**Controller:** [Operator legal name], [contact email]. **Effective date:** [date].

## What we collect
- **Account data:** first, middle (optional) and last name, email address, an auto-generated username, a bcrypt hash of your password (never the password itself), your role, and account creation and last-login times.
- **Project data:** prompts, generated specifications, page designs, design tokens, data-model definitions, records submitted through preview forms, uploaded images, version snapshots, messages with the AI assistant, project memory notes, and AI task logs.
- **Security and operations data:** session records (hashed refresh tokens and browser user-agent), audit events (for example login, failed login, export, deletion) including IP address, request logs with request IDs, and AI usage records (task, model, token counts, status, duration).
- **Reference websites:** if you supply a URL, we fetch publicly accessible pages from that site and store a structural summary in your project.

We do not sell personal data and we do not use advertising trackers.

## How AI requests are processed
To generate and modify Projects we send the relevant parts of your project to **Groq, Inc.** for inference: your prompt, the project specification, design tokens, page and section outlines, data-model definitions, the selected element (for edits), a summary of a reference website (if provided), and recent assistant messages. We do not send your password or email address. Groq processes this data under its own terms and privacy policy, available at https://groq.com/privacy-policy/. Requests use one platform-owned API key; inside AIDevs they are attributed to your account only for usage limits.

## Why we process data
To provide the service you request, to keep it secure and prevent abuse, and to meet legal obligations. [Legal bases to be confirmed with counsel.]

## Storage and security
Data is stored in a PostgreSQL database operated by our hosting provider ([provider, region]). Passwords are hashed with bcrypt; sessions use short-lived tokens with revocable, hashed refresh tokens; generated-site previews run in a sandboxed, isolated browser frame. No system is perfectly secure.

## Retention
See the [Data Retention and Deletion policy](/legal/data-retention).

## Your choices and rights
- **Export:** download all your data as JSON from Account, "Download my data", and export any project as source code from the Studio.
- **Delete:** delete your account from Account, "Delete account" (immediate and permanent).
- **Other requests:** contact [contact email]. Depending on where you live you may have rights to access, correct, delete, restrict or object to processing, and to complain to a supervisory authority.

## Children
The service is not directed to children under [age].

## Changes
We will post updates here and change the effective date.
