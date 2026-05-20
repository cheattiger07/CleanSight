# CleanSight — Intelligent Data Cleaning & Quality Automation Platform

CleanSight is a production-grade **data cleaning and quality analysis web application** built to automate one of the most time-consuming tasks in data science: preparing messy real-world datasets.

Users can upload raw **CSV or Excel files**, and CleanSight automatically detects, analyzes, and fixes common data quality issues such as:

* missing values
* duplicate rows
* schema inconsistencies
* datatype mismatches
* formatting errors
* outliers
* invalid records

It then generates a full **data quality report**, assigns a **quality score**, provides **AI-powered cleaning recommendations**, and allows users to export cleaned datasets in multiple formats.

---

## Features

### File Upload

* Supports `.csv`, `.xlsx`, `.xls`
* Handles encoding issues (`utf-8`, `latin1`)
* Validates duplicate headers and empty datasets

### Automated Cleaning Engines

* Schema validation engine
* Missing value engine
* Formatting engine
* Datatype correction engine
* Duplicate detection engine
* Outlier handling engine

### Quality Analytics

* dataset profiling
* missing-value analysis
* duplicate summary
* numeric/text column detection
* quality scoring engine

### AI Recommendations

Generates human-readable suggestions such as:

* standardize date formats
* remove duplicates
* fix invalid emails
* fill missing values

### Export Options

* Cleaned CSV
* Professional Excel report
* PDF quality report

### Production Ready

* modular architecture
* Flask backend
* responsive frontend
* deployed on Render
* scalable design

---

## Tech Stack

* Python
* Flask
* Pandas
* OpenPyXL
* HTML/CSS/JavaScript
* Jinja2
* Render

---

## Why I Built This

CleanSight was built as a real-world portfolio project to solve a genuine industry problem:
**data cleaning consumes 60–80% of a data scientist’s time**.

This tool automates that process and demonstrates production-grade backend engineering, data processing, and SaaS product thinking.

---

## Future Roadmap (v2)

* multi-file uploads
* async large-file processing
* AI-assisted cleaning
* REST API access
* SaaS subscriptions
* team workspaces
* audit logs
