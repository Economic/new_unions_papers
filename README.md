# Union Research Papers Tracker

Automated tracking system for union research papers from OpenAlex API, NBER, and IZA.

## How it works

Three GitHub Actions workflows:
1. **Daily data fetch**: `union_papers.R` queries APIs, filters out false hits, updates CSV database
2. **Weekly Slack notifications**: `send_slack.py` sends formatted messages for new papers
3. **Website deployment**: Publishes interactive table to GitHub Pages when data changes

Papers are tracked for 365 days and filtered to include mentions of unions and to exclude papers with hits unrelated to labor unions.

## Setup

### Required GitHub Secrets

- **OPENALEX_EMAIL**: Email for OpenAlex API polite access
- **SLACK_WEBHOOK_URL**: Slack Incoming Webhook URL for notifications
- **PAT_GITHUB**: Personal access token for pushing commits from workflows

See `CLAUDE.md` for detailed documentation.
