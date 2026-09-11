---
title: "API rate limiting and throttling patterns"
source_topic: "API rate limiting and throttling patterns"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

Rate limiting protects a backend from being overwhelmed by a single client and
gives multiple tenants fair access to shared capacity. Common algorithms
include the token bucket (a bucket refills at a fixed rate and each request
consumes a token, allowing short bursts), the leaky bucket (requests are
processed at a constant output rate regardless of arrival burstiness), fixed
window counters (simple but allow a burst at window boundaries), and sliding
window logs or counters (smooth out the boundary problem at the cost of more
memory). For public APIs, rate limits are commonly communicated through
response headers indicating remaining quota and reset time, and a 429 status
code signals that the client should back off, ideally with a Retry-After
header. For agent systems calling external tools, client-side rate limiting
combined with exponential backoff and jitter prevents thundering-herd retries
during transient outages.
