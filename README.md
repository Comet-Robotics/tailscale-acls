# tailscale-acls

Tailnet policy file (ACLs) for the `comet-robotics.org.github` tailnet, managed via GitOps.

## How to change ACLs

1. Open a PR against `main` editing [`policy.hujson`](policy.hujson).
2. CI runs `action: test`, which validates the syntax and runs any `tests` blocks
   against the live tailnet.
3. Get a review, then merge. CI runs `action: apply` on `main`, which pushes the
   policy to the tailnet.

## Formatting

`policy.hujson` is [HuJSON](https://github.com/tailscale/hujson): JSON with comments and trailing commas. 
In the policy, we want to make sure that we have well-formed HuJSON, and that every member of a `groups` or
`tagOwners` list is on its own line, to minimize diffs and make editing ACLs and reviewing changes easier.

We have a small script that runs on PRs to check this:
```
python3 scripts/fmt_policy.py           # fix in place
python3 scripts/fmt_policy.py --check   # what CI runs
```

### The check comment

Every PR gets one comment from `github-actions[bot]` saying whether that check
passed, with the diff it produced. It's rewritten in place on each push, so you get
one comment per PR instead of one per run.

If it failed, the comment has a **"Format it for me"** checkbox. Tick it — or
comment `/fmt` — and [`lint-fix.yml`](.github/workflows/lint-fix.yml) runs the
formatter and commits the result to your branch. (There's no emoji-reaction
trigger because GitHub Actions has no event for reactions; ticking a checkbox
fires `issue_comment: edited`, which is the closest thing.) It needs write access,
since it pushes a commit, and it can't push to a fork — fork authors get told to
run the formatter locally instead.

One wrinkle: a commit pushed by `GITHUB_TOKEN` doesn't start a new workflow run,
and **re-running the `acls` check won't help**, because a re-run reuses the commit
that triggered the original run. To get a fresh run on the formatted commit, push
any commit (`git commit --allow-empty -m rerun && git push`) or close and reopen
the PR. Reopening works even without write access, so it's the one a fork author
can use.

Two notes for anyone editing the workflow:

- The lint is a step **inside** the `acls` job on purpose. `acls` is the required
  check in the "Protect main" ruleset, and a separate lint job would leave `acls`
  skipped on failure — a skipped required check counts as passing, which would
  remove the merge gate. The comment comes from a separate `report` job that isn't
  required and holds the only `pull-requests: write` token.
- `workflow_dispatch` looks like a way to retrigger the check (dispatch events are
  exempt from the `GITHUB_TOKEN` rule) but isn't safe here: `Test ACL` only runs on
  `pull_request`, and a branch-ref OIDC subject isn't trusted by either tailnet
  credential, so a dispatched run would report a green `acls` that never tested the
  policy.

