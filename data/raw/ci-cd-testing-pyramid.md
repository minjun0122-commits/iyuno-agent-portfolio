---
title: "CI/CD and the testing pyramid"
source_topic: "CI/CD and the testing pyramid"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

The testing pyramid recommends a large base of fast, isolated unit tests,
a smaller layer of integration tests that exercise multiple components
together, and a thin top layer of end-to-end tests that exercise the whole
system through its real interfaces, because end-to-end tests are the slowest
and most brittle. Continuous integration runs this test suite automatically
on every change, typically gating merges on a passing build, and continuous
deployment (or delivery) automates promoting a passing build toward
production. For a project with an evaluation-heavy component such as an
LLM agent, teams often add a fourth, separate layer: a regression evaluation
suite that runs against a fixed question set to catch quality regressions
that ordinary unit tests would not detect, since a code change can pass all
unit tests while quietly making retrieval or answers worse.
