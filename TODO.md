# Firewall TODO

Each firewall should align with its OAuth provider / connector in vm0.

## High Priority

Commonly used connectors with fine-grained permission/scope systems.

- [ ] Notion — capabilities permission system
- [ ] Linear — OAuth scopes
- [ ] Atlassian (Jira) — OAuth scopes
- [ ] Atlassian (Confluence) — OAuth scopes
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
- [ ] Microsoft Graph (Outlook Mail) — OAuth scopes, very large API surface
- [ ] Microsoft Graph (Outlook Calendar) — OAuth scopes
- [ ] Supabase — OAuth
- [ ] PostHog — API key
- [ ] Airtable — OAuth scopes
- [ ] ClickUp — OAuth
- [ ] Zendesk — OAuth

## Done

- [x] GitHub — auto-generated from `github/docs` server-to-server-permissions.json
- [x] Slack — auto-generated from `slack-ruby/slack-api-ref`
- [x] Gmail — auto-generated from Google Discovery API
- [x] Google Sheets — auto-generated from Google Discovery API
- [x] Google Docs — auto-generated from Google Discovery API
- [x] Google Drive — auto-generated from Google Discovery API
- [x] Google Calendar — auto-generated from Google Discovery API
