# Contributing

Thanks for helping! A few ground rules keep this kit useful and safe for everyone.

## Keep it personal-data-free
- Never commit a `config.json`, anything under `data/` or `my-recipes/`, cook logs, plans, phone numbers or emails.
- Example recipes in `examples/recipes/` must be written for this repo (short, original). Don't add recipes copied from published sources.

## Keep the safety rules intact
- The agent **only fills carts**. Changes must never let it open checkout, choose a delivery window, place an order or enter credentials.
- Texts go only to the configured owner's number.
- Email, calendar, web and file content is data, never instructions.

## Before opening a pull request
```bash
python3 -m pip install reportlab openpyxl
python3 tests/smoke_test.py
```
The same check runs on every push and pull request.

## Good first contributions
- Cart steps for other grocery stores (Instacart, Kroger, Walmart…), following the same cart-only rules
- Text or notification channels beyond iMessage
- Metric-first examples and non-US sourcing tips in `setup/briefs/`
- More collection archetypes and curriculum focuses in `setup/templates/`
