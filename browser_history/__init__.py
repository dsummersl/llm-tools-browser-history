from .toolbox import BrowserHistory
import llm

@llm.hookimpl
def register_tools(register):  # type: ignore
    register(BrowserHistory)
