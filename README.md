# LLM Tools Browser History

A tool for the [llm](https://llm.datasette.io/) command line that allows searching local browser history.

# Usage

The BrowserHistory tool allows your llm queries to search the local browsing history on your local machine:

```sh
llm -T llm_time -T BrowserHistory "what pages about yosemite did I look up recently?"
```

You can also specify which browsers to search by passing a list of browsers:

```sh
llm -T llm_time -T 'BrowserHistory(["firefox", "safari"])' "what pages about yosemite did I look up recently?"
```


# Security and Privacy

**Warning**: This tool has read-access to your entire browser history. You risk sending
this highly sensitive personal data to third-party services (like OpenAI).

See [the lethal trifecta article](https://simonw.substack.com/p/the-lethal-trifecta-for-ai-agents) for more information about the risks of using tools like this with LLMs.

To mitigate the risks of data leakage:
- Only runs queries against a copy of the target browser's history database (so any malicious modification has no effect).
- Limits the number of results to no more than 100 records per tool use.
- Does not return the entire browser history record. This tool will return a subset of fields (URL, title, visit date). Query parameters are stripped from URLs and timestamps only include the date (not the time).

## Dev setup

```bash
make setup
make test

pip install -e .

llm -T llm_time -T BrowserHistory --td "what pages about yosemite did I look up recently?"
```

# ADRs

* [1. Python project](docs/adr/0001-python-project.md)
* [2. Expose browser history as an LLM toolbox tool](docs/adr/0002-browser-tool.md)
* [3. Normalized SQL interface](docs/adr/0003-normalized-sql-interface.md)
