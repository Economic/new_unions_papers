#!/usr/bin/env python3
"""
Send Slack notification for new union papers.

This script:
1. Reads union_papers_to_email.csv for new papers
2. Formats them into a Slack message with Block Kit formatting
3. Sends the message via Slack Webhook
4. Updates emailed_papers.csv to track what has been sent
"""

import os
import sys
import csv
from datetime import datetime
from typing import List, Dict
import json
import urllib.request
import urllib.error


def read_papers_to_notify(csv_path: str = 'union_papers_to_email.csv') -> List[Dict]:
    """Read papers that need to be sent in notification."""
    if not os.path.exists(csv_path):
        print(f"No {csv_path} file found.")
        return []

    papers = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        papers = list(reader)

    # Sort by publication date (descending)
    papers.sort(key=lambda x: x.get('publication_date', ''), reverse=True)
    return papers


def read_emailed_papers(csv_path: str = 'emailed_papers.csv') -> set:
    """Read the list of paper IDs that have already been emailed."""
    if not os.path.exists(csv_path):
        return set()

    emailed_ids = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            emailed_ids.add(row['openalex_id'])

    return emailed_ids


def update_emailed_papers(papers: List[Dict], csv_path: str = 'emailed_papers.csv'):
    """Update the emailed papers tracking file."""
    # Read existing emailed papers
    emailed_ids = read_emailed_papers(csv_path)

    # Add new paper IDs
    for paper in papers:
        emailed_ids.add(paper['openalex_id'])

    # Write back to file (sorted)
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['openalex_id'])
        for paper_id in sorted(emailed_ids):
            writer.writerow([paper_id])

    print(f"Updated {csv_path} with {len(papers)} new paper(s).")


def escape_slack_text(text: str) -> str:
    """Escape special characters for Slack mrkdwn format."""
    if not text:
        return ""
    # Escape &, <, and >
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def format_slack_message(papers: List[Dict]) -> Dict:
    """
    Format papers into Slack Block Kit message.

    Slack Block Kit documentation: https://api.slack.com/block-kit
    """
    paper_count = len(papers)
    paper_word = "paper" if paper_count == 1 else "papers"
    have_word = "has" if paper_count == 1 else "have"
    week_end_date = datetime.now().strftime("%B %d, %Y")

    # Build the blocks for the message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📚 New Union Papers Detected",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"The following *{paper_count} new {paper_word}* {have_word} been added to the <https://economic.github.io/new_unions_papers/|Recent Union Papers> list:"
            }
        },
        {
            "type": "divider"
        }
    ]

    # Add each paper as a section
    for paper in papers:
        # Escape special characters
        title = escape_slack_text(paper.get('title', ''))
        authors = escape_slack_text(paper.get('authors', ''))
        journal = escape_slack_text(paper.get('journal', ''))
        doi = paper.get('doi', '')
        publication_date = paper.get('publication_date', '')

        # Create the paper block
        paper_text = f"*{authors}*\n_{title}_\n"

        # Add journal with link if DOI exists
        if doi and journal:
            paper_text += f"📄 <{doi}|{journal}>"
        elif journal:
            paper_text += f"📄 {journal}"

        # Add publication date
        if publication_date:
            if doi or journal:
                paper_text += f"  |  📅 {publication_date}"
            else:
                paper_text += f"📅 {publication_date}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": paper_text
            }
        })

    # Add footer
    blocks.extend([
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Automated notification from the Union Papers tracking system_"
                }
            ]
        }
    ])

    return {
        "text": f"New union papers for the week ending {week_end_date}",  # Fallback text for notifications
        "blocks": blocks
    }


def send_slack_message(webhook_url: str, message: Dict) -> bool:
    """
    Send message to Slack via webhook.

    Returns True if successful, False otherwise.
    """
    try:
        # Convert message to JSON
        data = json.dumps(message).encode('utf-8')

        # Create request
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        # Send request
        with urllib.request.urlopen(req) as response:
            response_text = response.read().decode('utf-8')

            if response.status == 200 and response_text == 'ok':
                print("✓ Slack message sent successfully")
                return True
            else:
                print(f"✗ Unexpected response from Slack: {response.status} - {response_text}")
                return False

    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error sending Slack message: {e.code} - {e.reason}")
        print(f"  Response: {e.read().decode('utf-8')}")
        return False
    except urllib.error.URLError as e:
        print(f"✗ URL Error sending Slack message: {e.reason}")
        return False
    except Exception as e:
        print(f"✗ Error sending Slack message: {str(e)}")
        return False


def main():
    """Main execution function."""
    # Read papers to notify
    papers = read_papers_to_notify()

    # Check if there are any papers to notify about
    if not papers:
        print("No new papers found. Skipping Slack notification.")
        sys.exit(0)

    paper_count = len(papers)
    paper_word = "paper" if paper_count == 1 else "papers"
    print(f"Found {paper_count} new {paper_word}. Preparing Slack message...")

    # Get Slack webhook URL from environment
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')

    if not webhook_url:
        print("✗ Error: SLACK_WEBHOOK_URL environment variable is not set")
        sys.exit(1)

    # Format the message
    message = format_slack_message(papers)

    # Send to Slack
    success = send_slack_message(webhook_url, message)

    if not success:
        print("Failed to send Slack message")
        sys.exit(1)

    # Update emailed papers tracking file
    update_emailed_papers(papers)

    print(f"\n✓ Successfully sent notification for {paper_count} {paper_word}.")


if __name__ == '__main__':
    main()
