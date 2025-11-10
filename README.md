# Union Research Papers Tracker

Automated tracking system for union research papers from OpenAlex API, NBER, and IZA.

## How it works

Three GitHub Actions workflows:
1. **Daily data fetch**: `union_papers.R` queries APIs, filters out currency/European union papers, updates CSV database
2. **Weekly Slack notifications**: `send_slack.py` sends formatted messages for new papers
3. **Website deployment**: Publishes interactive table to GitHub Pages when data changes

Papers are tracked for 365 days and filtered to exclude papers that only mention "currency union" or "European Union".

## Setup

### Required GitHub Secrets

- **OPENALEX_EMAIL**: Email for OpenAlex API polite access
- **SLACK_WEBHOOK_URL**: Slack Incoming Webhook URL for notifications
- **PAT_GITHUB**: Personal access token for pushing commits from workflows

See `CLAUDE.md` for detailed documentation.
