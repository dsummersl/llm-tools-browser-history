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

## Dev setup

```bash
make setup
make test
```


# ADRs

Architecture Decision Records live in docs/adr.
