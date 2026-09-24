# ARHPP Deployment

Local development:

```bash
pip install -r requirements.txt
python -m excel_templates.build_templates
python -m api.server
```

Docker:

```bash
docker compose up -d
```
