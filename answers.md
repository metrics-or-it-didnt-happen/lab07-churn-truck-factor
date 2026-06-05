# Lab 07 - Answers

Target project: **Django** (https://github.com/django/django), 34 355 commits, 13 277 files.

## Task 1: git log --numstat Exploration

### Q1: Which 5 files were changed most frequently?

| # | File | Commits |
|---|------|--------:|
| 1 | `AUTHORS` | 1 120 |
| 2 | `django/db/models/query.py` | 628 |
| 3 | `django/db/models/sql/query.py` | 594 |
| 4 | `docs/ref/settings.txt` | 551 |
| 5 | `django/db/models/fields/__init__.py` | 534 |

`AUTHORS` dominates because every new contributor adds a line. The remaining four are core ORM and reference documentation — the heart of Django's data layer.

### Q2: Are those also the highest churn files?

No — there is **zero overlap** between the top 5 by frequency and the top 5 by churn.

**Top 5 by churn (adds + deletes):**

| # | File | Churn |
|---|------|------:|
| 1 | `django/conf/locale/es/LC_MESSAGES/django.po` | 56 752 |
| 2 | `django/conf/locale/it/LC_MESSAGES/django.po` | 42 411 |
| 3 | `django/conf/locale/ca/LC_MESSAGES/django.po` | 41 862 |
| 4 | `django/conf/locale/sk/LC_MESSAGES/django.po` | 39 906 |
| 5 | `django/conf/locale/fr/LC_MESSAGES/django.po` | 39 792 |

All top-churn files are locale translation files (`.po`). They change relatively infrequently (100 commits or fewer) but each update rewrites thousands of lines. Meanwhile, the most frequently changed files have moderate churn:

| File | Commits | Churn |
|------|--------:|------:|
| `AUTHORS` | 1 120 | 2 882 |
| `django/db/models/query.py` | 628 | 14 247 |
| `django/db/models/sql/query.py` | 594 | 14 957 |

This shows that **frequency and churn measure different things**: frequency tracks how often a file attracts attention (risk of conflicts, coordination cost), while churn tracks how much code is rewritten (instability, potential for bugs).

### Q3: How many unique authors touched the most-frequently-changed file?

`AUTHORS` has been touched by **557 unique authors** — unsurprising since adding yourself to `AUTHORS` is a standard step for new Django contributors.

Excluding the meta-file, `django/db/models/query.py` (2nd most changed) has been touched by **172 unique authors**. Its top 5 contributors:

| Author | Commits |
|--------|--------:|
| Malcolm Tredinnick | 46 |
| Adrian Holovaty | 44 |
| Russell Keith-Magee | 41 |
| Simon Charette | 33 |
| Tim Graham | 31 |

No single author dominates — the top contributor has only 7.3% of commits, indicating healthy shared ownership of this critical file.

## Truck Factor Analysis

**Truck factor: 4**

The greedy set-cover algorithm identified 4 key developers whose departure would leave more than 50% of Django's files without a primary owner:

| Developer | Files owned |
|-----------|------------:|
| Claude Paroz | 2 903 |
| Tim Graham | 1 321 |
| Florian Apolloner | 1 321 |
| Jannis Leidel | 1 224 |

Claude Paroz alone owns 21.9% of all files — most of these are translation/locale files where he has served as the primary i18n maintainer. Tim Graham and Florian Apolloner cover large swaths of the test suite and admin code.

**Lonely islands:** 5 309 of 13 277 files (40.0%) have only one author. This is typical for a project of Django's size — many files are one-time additions (locale files, test fixtures, configuration) that rarely need updates.

### Risk assessment

A truck factor of 4 is **reasonable for a large OSS project**. The Django Software Foundation has an active team of fellows and maintainers that mitigates single-point-of-failure risk. However, the high concentration of ownership in locale/i18n files (Claude Paroz) and the admin subsystem represents a moderate risk if those maintainers were to leave. The core ORM, by contrast, has well-distributed ownership across many contributors.
