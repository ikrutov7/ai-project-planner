# Demo script

Сценарий для записи demo.gif / видео (~60–90 сек).

## Steps

1. Открыть приложение — виден seed Gantt (~20 задач) и чат справа.
2. **Import Excel** → выбрать `examples/sample-plan.xlsx` → диаграмма обновляется.
3. В чате: `Перенеси UX Wireframes на 7 дней позже` → бар сдвигается.
4. В чате: `Назначь Maya на design` → исполнители обновляются.
5. Клик по задаче → модалка с деталями → Save.
6. **Export Excel** → скачивается `plan.xlsx`.

## Recording tips

- 1440×900, 1.25× cursor
- Не показывать `.env` / API keys
- Если нет LLM-ключа — в шапке чата будет `Demo agent`
