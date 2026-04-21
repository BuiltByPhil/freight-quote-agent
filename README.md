# freight-quote-agent

An AI-powered agent that automates the retrieval, parsing, and comparison of freight shipping quotes across multiple carriers. Built on the Anthropic Claude API, it accepts shipment parameters, queries carrier APIs via tool use, and returns structured quote summaries with recommended options.

## Architecture

```
freight-quote-agent/
├── src/
│   ├── __init__.py
│   ├── agent/        # Claude agent loop and tool orchestration (sprint 2+)
│   ├── tools/        # Individual carrier API tool callables (sprint 2+)
│   └── prompts/      # System and user prompt templates (sprint 2+)
├── tests/
│   └── __init__.py
├── .env.example      # Required environment variable keys
├── requirements.txt
└── CLAUDE.md
```

> Architecture is a placeholder — implementation begins sprint 2.
