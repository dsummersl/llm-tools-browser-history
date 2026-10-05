from typing import Literal

BrowserType = Literal["chrome", "firefox", "safari"]


HISTORY_COLUMNS_TEMPLATE = """
          {browser_name} AS browser,
          '{profile_label}' AS profile,
          process_url_url({url_col}) AS url,
          {title_col} AS title,
          {referrer_url_expr} AS referrer_url,
          {date_expr} AS visited_dt,
          process_url_domain({url_col}) AS domain,
          process_url_stripped({url_col}) AS stripped_qp,
          {referrer_domain_expr} AS referrer_domain,
          {referrer_stripped_qp_expr} AS referrer_stripped_qp
"""
