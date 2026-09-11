---
title: "API authentication and authorization patterns"
source_topic: "API authentication and authorization patterns"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

OAuth 2.0 separates authentication (proving who a user is) from authorization
(what a client is allowed to do on the user's behalf) using short-lived access
tokens and longer-lived refresh tokens. OpenID Connect layers an identity
token on top of OAuth 2.0 for authentication use cases. API keys are simpler
but weaker: they typically identify an application rather than an individual
user and do not expire automatically, so they should be scoped narrowly and
rotated regularly. JSON Web Tokens (JWTs) let a server issue a signed,
self-contained token that a downstream service can verify without a database
round trip, but because a JWT cannot easily be revoked before its expiry,
systems that need fast revocation typically keep expiry windows short or
maintain a token-denylist.
