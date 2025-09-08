from typing import TypedDict, Literal

BrowserType = Literal["chrome", "firefox"]

class NormalizedRow(TypedDict):
    url: str
    title: str
    browser: BrowserType
    visited_at: str
    visit_count: int
    profile_path: str
