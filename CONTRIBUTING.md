# Contributing to Battered Aggie Syndrome

Thanks for helping make college football research more transparent, reproducible, and understandable.

This is a research preview. A contribution can improve the project without supporting a claim that A&M underperforms. Negative results and well-supported criticism are welcome.

## Before starting

Read the [project status](docs/public/STATUS.md), [research method](docs/public/RESEARCH_METHOD.md), and [data and reuse policy](docs/public/DATA_AND_REUSE.md). No code license has been selected; contributors should discuss substantial contributions and their intended licensing with the maintainer before submitting them.

Search existing issues before opening a new one. For a substantial model, dataset, or architecture change, propose the scope in an issue before implementing it.

## Good first contributions

- Clarify a confusing example or explain a statistical term.
- Add a tiny synthetic fixture for an edge case.
- Reproduce a data-identity, cutoff, or scoring defect without restricted data.
- Improve accessibility, link quality, or installation instructions.
- Propose an authoritative source with clear access and reuse terms.

## Report a bug

Include your Python version and OS, the commit you tested, minimal reproduction steps, expected versus actual behavior, and a small permitted example. Redact local usernames and paths where they are not necessary. Do not paste `.env` files, API keys, access tokens, private issue exports, or bulk provider responses.

Use the repository's private vulnerability-reporting channel if one is available for a security issue. Otherwise, request a private contact channel without posting exploit details or sensitive data. See [Security](SECURITY.md).

## Prepare a pull request

1. Create a focused branch and keep unrelated changes separate.
2. Add a regression test that demonstrates the defect before the fix.
3. Identify the data population and cutoff affected by a scientific change.
4. Run the focused tests and document the exact commands and results.
5. Update the public documentation if behavior or limitations change.
6. Describe remaining uncertainty, missing evidence, and any skipped checks.

Never replace a failing test with an unconditional skip to obtain a passing build. Never modify an immutable forecast to make it match the eventual result. A test pass is evidence about the test, not a scientific validation certificate.

## Scientific review checklist

- Is every input justified at the relevant pregame cutoff?
- Is the actual target opponent used, rather than a historical opponent?
- Are outcomes kept out of the features for their own game?
- Are training and evaluation partitions chronological and game-separated?
- Do probabilities, margins, and intervals have a consistent interpretation?
- Are game counts distinguished from oriented team rows and model rows?
- Are market benchmarks separate from independent forecasts?
- Do reported claims match the tested artifacts and their limitations?

Some full-system checks require external research payloads and are not equivalent to the offline smoke tests. State exactly which environment and evidence were available. Maintainer review and all applicable merge controls remain required.

## Community expectations

Challenge methods and evidence, not people. Be respectful toward contributors, teams, coaches, and players. Do not submit unsupported allegations or private medical information. This project investigates football performance; it does not diagnose fans or athletes.
