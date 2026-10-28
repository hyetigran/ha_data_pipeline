# Staged-file token budget

The pre-commit hook rejects maintained text files over **20,000 bytes**, using the requested estimate of **tokens = bytes / 4**. Exactly 5,000 tokens is allowed. It checks the complete staged blob of each added, modified, renamed or type-changed regular file. It does not check unstaged content, unchanged files, deleted files, symlinks or submodules. Binary blobs containing a NUL byte in their first 8,000 bytes are skipped.

Git does not reliably identify agent authorship. The policy therefore covers maintained text whether written by an agent or a person. Lockfiles and known generated outputs are excluded through the `token-limit-exempt` attribute in [.gitattributes](../.gitattributes). Other extensions, including JSON, are checked by default. For additional genuine codegen or vendored output, add a specific path or narrow pattern to that file. The hook reads attributes from the index, so stage the exclusion alongside the generated file. Do not exempt maintained source to avoid splitting it.

Enable the versioned hook in each clone:

```sh
git config --local core.hooksPath .githooks
```

The hook uses `.venv/bin/python` when available and otherwise `python3`. It requires no extra Python packages. Run it manually against the current index with:

```sh
.githooks/pre-commit
```

On failure, extract code by responsibility into cohesive modules, move corresponding tests, and update callers. Split documents into topic pages with a short linking index, and split maintained fixtures by scenario. Keep every resulting file within the limit, run relevant checks, then stage all new files, changed callers and deletions before retrying. The error message repeats these instructions.

The hook is local Git enforcement; normal Git hook bypass mechanisms still exist. Existing oversized files are checked when staged for a change, not retroactively scanned on every commit.
