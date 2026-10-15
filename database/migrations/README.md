Actual Alembic migrations for the `inference_requests` table live in
`api-gateway/alembic/versions/`, since migrations are tied to the
API Gateway's SQLAlchemy models (`api-gateway/app/database/models.py`).

This folder is kept as a structural placeholder / documentation pointer
so the top-level layout matches the project's architecture doc. To run
migrations:

```bash
cd api-gateway
alembic upgrade head
```
