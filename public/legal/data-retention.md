# Data Retention and Deletion

> DRAFT — requires legal review. The periods below describe the current software behaviour; the operator must confirm hosting-provider backup retention.

## What is kept, and for how long
- **Account profile and password hash:** until you delete your account.
- **Projects, pages, data models, assets, versions, messages, project memory, AI task logs:** until you delete the project or your account.
- **Automatic version snapshots:** the latest 60 automatic snapshots per project; manual versions until deleted.
- **Preview form submissions:** until the project is deleted (at most 500 per project).
- **Refresh-token records:** expire after 30 days; purged with `python manage.py prune-tokens`.
- **AI usage records:** kept for capacity planning; detached from your identity when you delete your account.
- **Audit and security events:** kept for security investigation; detached from your identity when you delete your account. Operators should purge entries older than [N] days.
- **Database backups:** per hosting provider configuration, [N] days.

## Deleting your account
Account, Delete account (password plus typing DELETE). Deletion is immediate: your account, projects, pages, assets, versions, messages, memory and sessions are removed from the live database; usage and audit records are anonymised. Copies may persist in backups until those expire.

## Exporting your data
Account, Download my data (JSON). Projects can also be exported as runnable source code.
