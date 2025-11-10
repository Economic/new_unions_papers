# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an automated union research paper tracking system that:
1. Fetches papers from OpenAlex API, NBER, and IZA analyzing the effects of unions
2. Maintains a database of papers with status tracking (new/old/updated)
3. Sends Slack notifications for newly discovered papers
4. Publishes an interactive HTML table to GitHub Pages
5. Filters out papers that only mention "currency union" or "European Union" without other union references

The system runs via three separate GitHub Actions workflows that operate on different schedules.

## Key Files

### Scripts
- `union_papers.R` - Main data fetching and processing script. Queries OpenAlex API, NBER, and IZA, merges with existing data, tracks paper status (new/old/updated), filters out currency union/European Union papers, and generates CSV outputs.
- `send_slack.py` - Slack notification system. Sends formatted Slack messages via webhook for new papers. Uses Python standard library only (no external dependencies).
- `send_email.R` - (Legacy) Original email notification system, kept for reference but no longer used.
- `index.qmd` - Quarto document that renders the website, displaying papers in an interactive `reactable` table.

### Data Files
- `union_papers.csv` - Main database of all papers (last 365 days)
- `union_papers_to_email.csv` - Papers that need to be notified (status="new" AND not yet notified). Note: Name kept for backward compatibility despite Slack migration.
- `emailed_papers.csv` - Tracking file to prevent duplicate notifications. Note: Name kept for backward compatibility despite Slack migration.
- `initial_journals.csv` - List of journal ISSNs to query in OpenAlex

### GitHub Actions Workflows
- `.github/workflows/update_data.yml` - Runs daily at 5:30 AM UTC (`cron: '30 5 * * *'`). Executes `union_papers.R` and commits updated CSVs. Manual trigger via `workflow_dispatch`.
- `.github/workflows/send_slack.yml` - Runs weekly on Fridays at 9:30 AM UTC (`cron: '30 9 * * 5'`). Executes `send_slack.py` to notify about new papers via Slack and commits `emailed_papers.csv`. Manual trigger via `workflow_dispatch`.
- `.github/workflows/deploy_website.yml` - Triggers on push to main branch when `union_papers.csv` or `index.qmd` changes. Renders Quarto site and deploys to GitHub Pages. Manual trigger via `workflow_dispatch`.

## Architecture

### Data Pipeline Flow
1. **Fetch** (update_data.yml): `union_papers.R` queries APIs → filters out currency/European union papers → updates `union_papers.csv` and `union_papers_to_email.csv`
2. **Notify** (send_slack.yml): `send_slack.py` reads `union_papers_to_email.csv` → sends Slack message → updates `emailed_papers.csv`
3. **Publish** (deploy_website.yml): Quarto renders `index.qmd` using `union_papers.csv` → deploys to GitHub Pages

### Paper Status Tracking
The system maintains three states in `union_papers.R`:
- **new**: Paper appears in API fetch but not in existing CSV
- **old**: Paper exists in CSV but no longer appears in API fetch
- **updated**: Paper exists in both, but metadata has changed

Status tracking prevents duplicate notifications by maintaining two separate tracking mechanisms:
1. Status field in `union_papers.csv` (managed by `update_papers()` and `combine_papers()`)
2. Separate `emailed_papers.csv` tracking file (prevents re-notifying if paper status changes)

### Search Queries
- OpenAlex: Searches for "union" OR "unions" in journals matching ISSNs from `initial_journals.csv`. Looks back 365 days.
- NBER: Downloads full metadata TSV files, filters by regex matching "union" in title/abstract. Looks back 365 days.
- IZA: Scrapes IZA Discussion Papers website, filters by regex matching "union" in title/abstract. Looks back 2 months only (shorter window to minimize scraping load).
- Post-filtering: All papers mentioning "currency union" or "European Union" are filtered out unless they contain additional mentions of "union" in the title or abstract.

## Development Commands

### Local Testing
```bash
# Run data update script (requires OPENALEX_EMAIL environment variable)
Rscript union_papers.R

# Test Slack notification (requires SLACK_WEBHOOK_URL environment variable)
python send_slack.py

# Render website locally
quarto render index.qmd

# Preview rendered site
quarto preview index.qmd
```

### Manual Workflow Triggers
All workflows support `workflow_dispatch` for manual triggering via GitHub Actions UI:
1. Navigate to Actions tab in GitHub repository
2. Select the workflow from the left sidebar
3. Click "Run workflow" button
4. Select branch and confirm

### Required Environment Variables / GitHub Secrets
- `OPENALEX_EMAIL`: Email for OpenAlex API polite access
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL for sending notifications
- `PAT_GITHUB`: Personal access token for pushing commits from GitHub Actions

See `SLACK_SETUP.md` for detailed instructions on configuring Slack integration.

## R Package Dependencies

Dependencies are managed via GitHub Actions using `r-lib/actions/setup-r-dependencies@v2`, which reads from DESCRIPTION file (if present) or installs packages as needed.

### Core Data Processing (union_papers.R)
- `openalexR`: OpenAlex API client
- `dplyr`, `tidyr`, `purrr`: Data manipulation
- `readr`: CSV reading/writing
- `lubridate`: Date handling
- `stringr`: String operations
- `rvest`: HTML web scraping (for IZA)
- `httr`: HTTP requests

### Slack Notification (send_slack.py)
- Python 3.6+ standard library only (no external dependencies)
- Uses `urllib.request` for HTTP requests
- Uses `json` for message formatting
- Uses `csv` for data file handling

### Web Rendering (index.qmd)
- `readr`, `dplyr`: Data reading and manipulation
- `reactable`: Interactive HTML tables
- `htmltools`: HTML generation

## Important Implementation Details

### Data Retention
Papers are filtered to only include those with `first_retrieved_date >= Sys.Date() - 365`. This 365-day rolling window is applied in:
- `union_papers.R`: Final output filtering in `update_papers()` function
- `index.qmd`: Display filtering when reading the CSV

### Non-OpenAlex ID Handling
NBER papers use their paper ID (e.g., "w12345") as `openalex_id`, and IZA papers use "iza" + paper ID (e.g., "iza12345"). This allows unified tracking across all data sources, but means `openalex_id` is not always an actual OpenAlex ID.

### Currency Union / European Union Filtering
After fetching all papers, the system filters out papers that only mention "currency union" or "European Union". Papers are kept if:
- They don't mention either term at all, OR
- They mention these terms but also have additional mentions of "union" in the title or abstract

This is implemented by counting all occurrences of "union" and comparing against the count of "currency union" and "European Union" mentions. The filtering logic is case-insensitive.

### Core Functions in union_papers.R
- `update_papers(new, old)`: Main reconciliation function that handles null cases and calls `combine_papers()`
- `combine_papers(new, old)`: Identifies new, old, and common papers by comparing fetched data with existing CSV
- `create_common_papers(new, old)`: Detects which common papers have actually been updated by comparing metadata
- `clean_oa_papers(data)`: Transforms raw OpenAlex API response into standardized schema
- `nber_fetch()`: Downloads NBER metadata TSV files (ref, abs, jel) and joins them
- `iza_fetch()`: Web scraping implementation with polite delays and early stopping after 5 consecutive old papers
- `scrape_iza_paper(url)`: Individual paper scraper with error handling

### Slack Message Formatting
The `send_slack.py` script uses Slack's Block Kit format for rich message formatting. Special characters (&, <, >) are escaped for proper Slack mrkdwn rendering. Messages include:
- Header with paper count
- Link to the website
- Individual paper blocks with authors, title, journal, and publication date
- Clickable DOI links when available

### Website Mobile Responsiveness
The reactable table uses custom HTML cells with `data-label` attributes for responsive mobile display (see `styles.css` for mobile-specific CSS).

### IZA Scraping Strategy
IZA papers are fetched via web scraping with:
- Pagination through 2 pages (100 papers per page = 200 papers max)
- Early stopping after 5 consecutive papers before date range (typically stops much earlier than 200 papers)
- 1-second delays between requests (polite scraping)
- Shorter lookback window (2 months vs 365 days for other sources) to minimize scraping load
- Individual paper scraping with error handling to gracefully skip problematic pages
