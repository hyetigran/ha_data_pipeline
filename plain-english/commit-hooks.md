# Keep changed text files small

A Git commit saves a selected set of changes. A hook is a script that runs before the commit.

This hook blocks a changed text file if its staged version is over 20,000 bytes. It estimates one token as four bytes. Exactly 20,000 bytes is allowed.

It checks the whole staged file, not just the added lines. It does not check unchanged files or edits that you have not staged.

Generated files such as lockfiles can have specific exemptions in `.gitattributes`. Ordinary source files should be split by topic instead of exempted.

To enable the hook in this checkout:

```sh
git config --local core.hooksPath .githooks
```

To run it yourself:

```sh
.githooks/pre-commit
```

If a file is too large, split it into smaller files with clear jobs. Update links or imports, run the needed checks, and stage the new files before trying again.

The hook applies to both human-written and AI-written text. It is a local check, not a guarantee that nobody can bypass it.

---

[Start here](README.md) · [Original document](../docs/commit-hooks.md)
