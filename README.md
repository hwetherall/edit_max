# Investment Memo Editor

A tool that processes investment memos through multiple LLMs via OpenRouter, making them more succinct and readable, similar to top-tier VC firms like Sequoia or A16Z.

## Features

- Process markdown text through 6 reasoning LLMs
- Consolidate their edits into a final version using anthropic/claude-3.7-sonnet:thinking
- Compare performance with timing metrics for each model
- Save and view past results
- Choice of CLI or Streamlit GUI interface

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a .env file with your OpenRouter API key:

```bash
cp .env.example .env
# Edit .env with your API key
```

## Usage

### CLI Interface

Process a markdown document from a file:
```bash
python main.py process --file path/to/markdown.md
```

From stdin:
```bash
python main.py process
# Enter markdown text, then press Ctrl+D when finished
```

List saved results:
```bash
python main.py list
```

View a specific result:
```bash
python main.py view memo_edit_20230615_123045.json
```

### Streamlit GUI

Run the Streamlit app:
```bash
streamlit run app.py
```

The app provides an interface to:
- Paste or upload markdown text
- Select which models to use
- View outputs from each model with processing times
- Compare model performance with timing metrics
- See the final edited version
- Save results and export edited text

## Models Used

The following OpenRouter models are used:

- openai/gpt-4.1
- anthropic/claude-3.7-sonnet
- google/gemini-2.5-flash-preview-05-20
- x-ai/grok-3-beta
- meta-llama/llama-4-maverick
- deepseek/deepseek-chat-v3-0324

The final consolidation is done with:
- anthropic/claude-3.7-sonnet:thinking

## License

MIT # edit_max
