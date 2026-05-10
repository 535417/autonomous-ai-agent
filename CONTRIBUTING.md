# Contributing

Thank you for your interest in contributing to AI Research Digest Agent.

## How to contribute

1. Open an issue for new feature ideas, bug reports, or improvement proposals.
2. Fork the repository and create a topic branch.
3. Submit a pull request with a clear description of your changes.

## Development setup

1. Create a Python 3.11 virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure `.env` with required variables.
4. Run the agent:
   ```bash
   python main.py
   ```

## Environment variables

- `DEEPSEEK_API_KEY`: required for the DeepSeek/OpenAI-compatible API endpoint.
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_RECIPIENTS`: optional for email delivery.

## Contributions

- New RSS sources and trend analysis rules are welcome.
- Improvements to report structure or automation are encouraged.
- Bug fixes are especially valuable for stable daily generation.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
