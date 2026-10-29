I'm the senior engineer taking over this invoice approval service. In January it goes to production as a tier-2 service and starts submitting approved invoices to an external payment provider, PayEx. I need to decide how we guarantee that an approved invoice reaches PayEx exactly once.

Facts:
- ASP.NET Core 8 on Azure App Service (three instances behind a load balancer), Azure SQL, GitHub Actions. Azure Service Bus is provisioned and nothing uses it yet.
- Today the repository uses an in-memory store; the database is part of going to production.
- About 40,000 invoices a month, 60% of them in the last three working days, peaking near 80 approvals a minute.
- PayEx returns a reference on success. It times out at 30 seconds, and a timeout does not reliably mean the submission failed.
- SOC 2 Type II audit in six months. Approval actions must be auditable for seven years.
- Six engineers, two of them new to this codebase, one-week on-call rotation.

The code is in this repository, and the planned production setup is described under ops/ (the incident packs included).

Lay out the trade-offs between at least these three options, then recommend one:
1. an idempotency key with a dedupe table
2. a transactional outbox with a worker
3. optimistic submission with nightly reconciliation
