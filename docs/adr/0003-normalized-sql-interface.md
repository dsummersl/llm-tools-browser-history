# 3. Normalized SQL interface

Date: 2025-09-08

## Status

Accepted

## Context

The tool as it is allows simple searches and filters by title and date, but more complex queries cannot be expressed at all (group by domain, etc).

This tool also allows an enterprising using to export their entire history using the LLM tool.

## Decision

Refactor the BrowserHistory.search() method to accept a raw SQL query against a materialized view of all the browser history datasets.

The schema will be:

```sql
CREATE TABLE IF NOT EXISTS browser_history (
  browser     TEXT NOT NULL,          -- 'chrome' | 'firefox' | 'safari' | …
  profile     TEXT,                   -- optional label you add
  url         TEXT NOT NULL,
  title       TEXT,
  referrer_url TEXT,                  -- NULL on Safari
  visited_ms  INTEGER NOT NULL        -- Unix ms UTC
);
CREATE INDEX IF NOT EXISTS idx_bh_time ON browser_history(visited_ms);
CREATE INDEX IF NOT EXISTS idx_bh_url  ON browser_history(url);
```

Rather than allowing infinite responses, and all data, limit the output to a maximum of 100 rows, and only the columns:
- url (with all query parameters stripped out)
- title (the title of the page)
- date of the visit (excluding the time)

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
