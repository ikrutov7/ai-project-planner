Sample Excel fixtures for import testing.

- `sample-plan.xlsx` — export of the demo seed plan (RU headers).

Regenerate from seed:

```bash
make excel
# or: cd backend && . .venv/bin/activate && python -m app.seed.export_excel
```

In the Docker/platform demo the same file is served at `/examples/sample-plan.xlsx`.

Required columns: `задача`, `описание`, `исполнитель`, `длительность`, `предшественники`.
