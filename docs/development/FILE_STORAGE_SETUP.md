# F1.8 File Storage Setup

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `STORAGE_PROVIDER` | `memory` \| `local` \| `s3` | `memory` |
| `STORAGE_LOCAL_ROOT` | Local disk root when provider=`local` | `.hmore-private-storage` |
| `STORAGE_MAX_UPLOAD_BYTES` | Max upload size | `10485760` |
| `STORAGE_ALLOWED_CONTENT_TYPES` | Comma-separated MIME allow-list | pdf/jpeg/png/webp/txt/doc/docx |
| `S3_ENDPOINT_URL` | Optional custom endpoint (MinIO) | unset (AWS) |
| `S3_REGION` | Region | `eu-west-2` |
| `S3_BUCKET` | Private bucket name | required for `s3` |
| `S3_ACCESS_KEY_ID` | Access key | required for `s3` |
| `S3_SECRET_ACCESS_KEY` | Secret | required for `s3` |
| `S3_FORCE_PATH_STYLE` | Path-style addressing | `false` |

Never commit real credentials. Use `.env` locally (gitignored).

## Local development

```text
# apps/api/.env
STORAGE_PROVIDER=memory
# or
STORAGE_PROVIDER=local
STORAGE_LOCAL_ROOT=.hmore-private-storage
```

MinIO example:

```text
STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_REGION=us-east-1
S3_BUCKET=hmore-private
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_FORCE_PATH_STYLE=true
```

Ensure the MinIO/S3 bucket is **private** (no public read policy).

## Tests

```text
cd apps/api
pytest tests/test_f18_storage.py tests/test_rbac_registry.py -q
# With DATABASE_URL — includes org isolation + audit persistence:
pytest tests/test_f18_storage.py -q
```

Real S3 integration is opt-in (`STORAGE_PROVIDER=s3` + credentials). Default CI uses `memory` plus Postgres for metadata/RLS.
