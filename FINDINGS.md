# FINDINGS.md

## Executive Summary

This document summarizes the main issues identified and fixed in the document processing system as part of the engineering challenge.

The work focused on **security**, **performance**, and **reliability**, prioritizing problems that could realistically lead to data exposure, service instability, or scalability limitations.

All changes were implemented incrementally, with small, reviewable commits and without altering the public API contracts unless strictly necessary.

---

## Security Issues

### 1. SQL Injection Risk in Search Endpoint (Critical)

**What I found**  
The search endpoint built SQL queries using string interpolation with user input.

**Why it matters**  
This allowed SQL injection attacks, potentially exposing or modifying all stored documents.

**How I fixed it**  
Replaced string-based query construction with SQLAlchemy ORM filters, ensuring proper parameter binding and escaping.

---

### 2. Hardcoded Secrets and Unsafe Defaults (Critical)

**What I found**  
Sensitive configuration values, such as database credentials and secret keys, had hardcoded fallback defaults.

**Why it matters**  
Hardcoded secrets can be leaked through source control and prevent proper secret rotation.

**How I fixed it**  
Removed all hardcoded defaults and enforced configuration strictly via environment variables, failing fast when required values are missing.

---

### 3. Unsafe File Upload Handling (High)

**What I found**  
Uploaded filenames were used directly when building file paths, and uploaded files were not fully validated.

**Why it matters**  
This enabled path traversal attacks, disk exhaustion, and crashes caused by invalid or malformed files.

**How I fixed it**  
- Sanitized filenames and validated resolved paths  
- Enforced file size limits and allowed content types  
- Validated PDF magic bytes before processing  

---

### 4. Overly Permissive CORS Configuration (Medium)

**What I found**  
CORS was configured to allow all origins while credentials were enabled.

**Why it matters**  
This weakens browser security guarantees and increases exposure to cross-site attacks.

**How I fixed it**  
Restricted allowed origins, methods, and headers via explicit environment-based configuration.

---

## Performance Issues

### 5. Blocking I/O and CPU-Bound Work in Async Endpoints (Critical)

**What I found**  
File I/O and PDF parsing were performed synchronously inside async FastAPI endpoints.

**Why it matters**  
Blocking the event loop prevents the application from handling concurrent requests efficiently.

**How I fixed it**  
- Replaced blocking file writes with non-blocking async I/O  
- Offloaded CPU-intensive PDF parsing to a dedicated process pool  

---

### 6. N+1 Database Query Pattern (High)

**What I found**  
Related data (processing status) was fetched using one query per document.

**Why it matters**  
This causes unnecessary database round trips and degrades performance as the dataset grows.

**How I fixed it**  
Applied eager loading with SQLAlchemy to fetch related records efficiently in a bounded number of queries.

---

### 7. Missing Pagination on List and Search Endpoints (High)

**What I found**  
List and search endpoints returned unbounded result sets.

**Why it matters**  
Large datasets lead to excessive memory usage, long response times, and poor client-side behavior.

**How I fixed it**  
Added explicit pagination parameters with validation and sensible upper limits.

---

## Reliability Issues

### 8. Missing Cleanup on Partial Failures (High)

**What I found**  
Uploaded files were not removed if validation or processing failed.

**Why it matters**  
This leads to orphaned files accumulating on disk over time.

**How I fixed it**  
Ensured uploaded files are cleaned up on all failure paths.

---

### 9. Missing Transactional Boundaries (Medium)

**What I found**  
Related database operations were executed without clear transactional boundaries.

**Why it matters**  
Partial failures could leave the database in an inconsistent state.

**How I fixed it**  
Grouped related operations into a single transaction and ensured rollback on failure.

---

### 10. Physical Files Not Deleted on Document Removal (Medium)

**What I found**  
Deleting a document removed database records but left the associated file on disk.

**Why it matters**  
Disk usage grows over time and deleted data may remain accessible.

**How I fixed it**  
Deleted associated files during document removal and relied on cascade deletes for related database records.

---

## Maintainability Improvements

### 11. Separation of Concerns in Document Processing (Medium)

**What I found**  
PDF parsing logic was embedded directly in route handlers.

**Why it matters**  
This makes the code harder to test, reuse, and evolve.

**How I fixed it**  
Extracted PDF processing into a dedicated service module, keeping route handlers focused on request orchestration.

---

## Implemented Feature: Document Tagging

**Overview**  
Added support for tagging documents and filtering document lists by tag.

**Implementation Summary**  
- Introduced a many-to-many relationship between documents and tags  
- Enforced unique, normalized tag names  
- Added endpoints to attach and list tags per document  
- Enabled filtering documents by tag using efficient joins  

This feature was implemented without breaking existing API behavior.

---

## Notes on Further Improvements

Given additional time, the next steps would include:
- Authentication and authorization  
- Improved observability with metrics and structured logging  
- Background job processing for long-running document tasks  

---

## Estimated Effort

The identified critical and high-priority issues were addressed within the scope of this challenge.

A fully production-hardened version would require approximately **one additional week** of focused work.
