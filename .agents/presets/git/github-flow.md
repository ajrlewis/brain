# GitHub Flow Preset

Adopted for `ajrlewis/brain`, whose remote default branch is `main`. The repository is currently solo and has no commits; protection and the external-review decision remain tracked in `.agents/todos/TODO.md` until `main` exists.

Use this default when the repository has no documented Git workflow. Existing project-specific policy takes precedence, including an explicitly adopted rebase workflow.

## Branching

- Work on feature or fix branches, not directly on `main`.
- Start each branch from an up-to-date `main`.
- Use a concise, descriptive branch name.
- When work has a tracker identifier, include it and use the actual change type, such as `feature/ENG-123-add-export`, `fix/ENG-124-handle-empty-response`, or `chore/ENG-125-update-dependencies`; not every work item is a chore.
- Keep the branch focused on one logical change.
- Make focused local commits with clear messages.
- Never push directly to `main`.

## Sync Before Push Or PR Updates

Do not sync with `main` before every local commit. Commit locally as needed.

Before pushing the feature branch or opening or updating its pull request, fetch the latest `origin/main` and merge it into the feature branch:

```sh
git fetch origin
git merge origin/main
```

Run these commands while on the feature branch. If conflicts occur:

- resolve them on the feature branch, never directly on `main`;
- inspect the resolved diff carefully;
- rerun the relevant verification from `.agents/COMMANDS.md`;
- do not claim conflict resolution is complete until those checks have run;
- push only after the merge and verification succeed.

Merging `origin/main` is the default because it avoids rewriting shared history, avoids unnecessary force pushes, and is straightforward to audit. Do not replace an existing repository's documented rebase workflow; follow that policy instead.

## Push And Pull Request

After syncing and verifying:

```sh
git push -u origin <branch>
```

Open or update a pull request targeting `main`. Before considering it ready to merge:

- inspect CI and required status checks;
- inspect and address review feedback;
- confirm the branch still merges cleanly where practical;
- address failures instead of bypassing required checks;
- merge through the pull request into protected `main`.

Never force-push a shared branch unless repository policy explicitly permits it and the intent is clear. Never rewrite shared history casually. Prefer reversible, auditable Git operations.

## Repository Protection

Protect the remote default branch with a GitHub ruleset or branch protection policy when GitHub Flow is adopted. For shared repositories:

- require pull requests before merge;
- require at least one approving review;
- enforce protection for administrators;
- prevent direct pushes to the default branch;
- block force pushes and deletion of the default branch.

Require relevant CI or status checks when they exist, and require branches to be current with the default branch when the CI or merge strategy benefits from it.

In a solo repository, ask the maintainer whether an external approval is practical because authors cannot approve their own pull requests. Verify the effective remote settings when GitHub access is available; if access or administration permission is unavailable, record the unresolved work in `.agents/todos/TODO.md` rather than claiming protection is configured.
