from typing import TypedDict, Literal

BrowserType = Literal["chrome", "firefox", "safari"]

class NormalizedRow(TypedDict):
    url: str
    title: str
    browser: BrowserType
    visited_at: str | None
    visit_count: int
    profile_path: str
