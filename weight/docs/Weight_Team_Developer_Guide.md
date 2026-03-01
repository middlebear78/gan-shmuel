# Weight Team — Developer Guide

## Setup

```bash
# Switch to weight branch
cd gan-shmuel
git checkout weight

# Create venv (MUST be named "venv" — it's in .gitignore)
cd weight
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Make sure MySQL is running before starting the app. Two options:
- **Local MySQL**: install and run on localhost
- **Docker**: `docker compose -f docker-compose.dev.yaml up`

For Docker, create a `.env` file from the example first:
```bash
cp .env.example .env
# Edit .env with: WEIGHT_DATABASE=weight, WEIGHT_ROOT_PASSWORD=<your password>, DB_USER=root
```

Connection details are in config.py (reads from environment variables, defaults to localhost).

```bash
python app.py
```

## Git Workflow

Each developer creates a feature branch off weight for each task:

```
weight-health-endpoint
weight-post-weight
weight-get-weight
weight-batch-weight
```

Daily workflow:

```bash
# 1. Switch to weight and pull latest
git checkout weight
git pull origin weight

# 2. Create a feature branch for your task
git checkout -b weight-your-feature

# 3. Work, commit as you go
git add .
git commit -m "Add GET /health endpoint"
git push origin weight-your-feature        # backup your work

# 4. When your feature is ready:
#    Back-merge weight, test, then submit a PR
git checkout weight
git pull origin weight
git checkout weight-your-feature
git merge weight
#    (resolve conflicts if any, test everything)
git push origin weight-your-feature

# 5. Go to GitHub → Create Pull Request
#    Target branch: weight (NOT staging, NOT main)
#    Reviewer: Michael

# 6. After PR is merged, clean up
git checkout weight
git pull origin weight
git branch -d weight-your-feature
```

**Important:**
- Back-merge weight into your branch BEFORE submitting a PR
- Test after every back-merge
- PRs to weight require Michael's approval
- Do NOT push directly to `weight`, `staging`, or `main`

## Folder Structure

```
weight/
├── app.py
├── config.py
├── database.py
├── models.py
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile.weight.dev
├── Dockerfile.mysql.dev
├── docker-compose.dev.yaml
├── db/
│   └── weightdb.sql
├── in/
│   ├── containers1.csv
│   ├── containers2.csv
│   └── trucks.json
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_post_weight.py
    ├── test_get_weight.py
    ├── test_batch_weight.py
    ├── test_item.py
    ├── test_session.py
    ├── test_unknown.py
    └── test_e2e_flow.py
```

## Testing

**Developers** write unit tests. **Team leads + DevOps** handle integration tests near the end of the project.

One test file per feature:

```
tests/
├── test_health.py
├── test_post_weight.py
├── test_get_weight.py
├── test_batch_weight.py
├── test_item.py
├── test_session.py
├── test_unknown.py
└── test_e2e_flow.py
```

Inside each file, use mock data (no DB needed):

```python
# tests/test_post_weight.py
from unittest.mock import patch

def test_neto_calculation():
    assert calculate_neto(15000, 4500, [296, 273]) == 9931

def test_neto_unknown_container():
    assert calculate_neto(15000, 4500, [296, None]) == "na"
```

The developer who builds the feature writes its unit tests.

Run all tests: `DB_PASSWORD=<your .env password> pytest tests/`
Run one file: `DB_PASSWORD=<your .env password> pytest tests/test_post_weight.py -v`

**Manual testing during development:**
Before submitting a PR, also test your endpoint manually:
- Use **curl** or **Postman** to send requests and verify responses
- Check valid input returns the correct response
- Check invalid input returns proper error codes (400, 404, 500)
- Check edge cases from the API spec (e.g., duplicate "in" with force=false)

## Before Submitting a PR — Checklist

- [ ] Endpoint returns correct response for valid input
- [ ] Endpoint returns proper HTTP errors (400, 404, 500)
- [ ] Edge cases from the API spec are handled
- [ ] Tested manually with curl or Postman
- [ ] Unit test file created/updated for your feature (tests/test_your_feature.py)
- [ ] All existing tests pass: `pytest tests/`
- [ ] Back-merged latest weight branch and resolved conflicts
- [ ] PR targets the `weight` branch with Michael as reviewer

## Conventions

- **venv name**: always `venv`
- **Don't commit**: venv/, .env, __pycache__/
- **Do commit**: .env.example, tests/, requirements.txt
- **Test dependencies**: add `pytest` and `requests` to requirements.txt
- **ORM**: SQLAlchemy via flask-sqlalchemy. Models in `models.py`, db object in `database.py`
- **DB driver**: pymysql (+ cryptography for MySQL 9 auth)
- **Feature branches**: use `weight-feature-name` (not `weight/feature-name` — git can't handle it since `weight` branch exists)
- **Weights**: store everything in kg internally. Convert lbs on input.
- **Datetime format in API**: yyyymmddhhmmss (e.g., 20260226130000)
- **Response for unknown neto**: return string "na" (not null, not 0)
