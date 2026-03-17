# Firewall TODO

## High Priority

Commonly used connectors with fine-grained permission/scope systems.

- [ ] Google (Gmail, Drive, Docs, Sheets, Calendar) — OAuth scopes, Discovery API doc
- [ ] Notion — capabilities permission system
- [ ] Linear — OAuth scopes
- [ ] Atlassian (Jira, Confluence) — OAuth scopes
- [ ] HubSpot — OAuth scopes

## Medium Priority

Commonly used with simpler permission models.

- [ ] Asana — OAuth
- [ ] Figma — OAuth scopes
- [ ] Stripe — REST API
- [ ] Dropbox — OAuth scopes
- [ ] Vercel — OAuth scopes
- [ ] Sentry — OAuth scopes
- [ ] Monday.com — OAuth scopes

## Low Priority

API key auth or smaller usage.

- [ ] OpenAI — API key, group by endpoint
- [ ] Microsoft Graph (Outlook Mail, Calendar) — OAuth scopes, very large API surface
- [ ] Supabase — OAuth
- [ ] PostHog — API key
- [ ] Airtable — OAuth scopes
- [ ] ClickUp — OAuth
- [ ] Zendesk — OAuth

## Done

- [x] GitHub — auto-generated from `github/docs` server-to-server-permissions.json
- [x] Slack — auto-generated from `slack-ruby/slack-api-ref`
