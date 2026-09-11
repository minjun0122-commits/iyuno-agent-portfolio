---
title: "Secure coding: input validation and output encoding"
source_topic: "Secure coding: input validation and output encoding"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

Most injection vulnerabilities stem from mixing untrusted data with a
command, query, or markup interpreter without proper separation. The most
robust defense is to use parameterized queries or prepared statements for
databases, so that user input is always treated as data rather than as part
of the query structure, and to use context-aware output encoding when
rendering user-controlled content into HTML, JavaScript, or URLs. Allow-list
validation (checking that input matches an expected format) is preferred over
deny-list validation (blocking known-bad patterns), because deny-lists are
easy to bypass with encoding tricks or unanticipated variants. Defense in
depth adds a web application firewall and strict content-security-policy
headers as additional layers, but these are not substitutes for fixing the
underlying handling of untrusted input in application code.
