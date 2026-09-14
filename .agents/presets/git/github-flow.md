# GitHub Flow Preset

Adopted for `ajrlewis/mind`, whose remote default branch is `main`. The repository is solo and does not currently protect `main`; protection and the external-review decision remain tracked in `.agents/todos/TODO.md`.

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

## Delivery Shortcut

When the user asks to "branch add commit push and PR," treat that phrase, or a clear equivalent, as authorization to complete the full delivery sequence:

1. Inspect the worktree and diff and identify the files belonging to the requested change.
2. If still on `main`, create and switch to a concise feature or fix branch. Otherwise, keep the current branch when it already represents the change.
3. Run the relevant verification from `.agents/COMMANDS.md`.
4. Stage only the intended files and preserve unrelated user changes.
5. Commit with a descriptive message.
6. Fetch `origin` and merge `origin/main` as described above. If the merge changes files, rerun the affected verification.
7. Push the branch with upstream tracking.
8. Open a pull request targeting `main` and return its URL.

Do not stop between these steps merely to request confirmation that the phrase already provides. Stop when a conflict, failed check, missing credential, or other condition requires user input or additional authority.

## After A Pull Request Is Merged

When the user reports "PR merged," treat that phrase, or a clear equivalent, as a request to update `main` and clean up the associated local branch:

1. Identify and remember the associated feature branch before switching. If it is unclear, ask before deleting anything.
2. Require a clean worktree; do not stash or discard changes implicitly.
3. Switch to `main`.
4. Update and prune remote-tracking state with `git pull --ff-only --prune`.
5. Show the branches Git recognizes as merged with `git branch --merged main`.
6. Delete the associated feature branch with `git branch -d -- <branch>`.

Never use `git branch -D` automatically. Squash or rebase merges may leave Git unable to prove that the local branch is merged; report that condition instead of forcing deletion.

## Repository Protection

Protect the remote default branch with a GitHub ruleset or branch protection policy when GitHub Flow is adopted. For shared repositories:

- require pull requests before merge;
- require at least one approving review;
- enforce protection for administrators;
- prevent direct pushes to the default branch;
- block force pushes and deletion of the default branch.

Require relevant CI or status checks when they exist, and require branches to be current with the default branch when the CI or merge strategy benefits from it.

In a solo repository, ask the maintainer whether an external approval is practical because authors cannot approve their own pull requests. Verify the effective remote settings when GitHub access is available; if access or administration permission is unavailable, record the unresolved work in `.agents/todos/TODO.md` rather than claiming protection is configured.
