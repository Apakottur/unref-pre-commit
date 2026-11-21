# unref-pre-commit

A [pre-commit](https://pre-commit.com/) and [prek](https://prek.j178.dev/) hook for
[unref](https://github.com/Apakottur/unref), an extremely fast Python dead code finder.

It is a separate repository so that the hook installs the prebuilt wheel of unref from
[PyPI](https://pypi.org/project/unref/), rather than building unref from source.

## Usage

Add the hook to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Apakottur/unref-pre-commit
    rev: v0.4.0
    hooks:
      - id: unref
```

The hook checks the whole project rather than the changed files, as finding unused code needs every file. To
configure unref, see its [documentation](https://github.com/Apakottur/unref).

## Versions

Each release of unref on PyPI is mirrored here as a tag of the same version, by a workflow that checks PyPI every
hour.
