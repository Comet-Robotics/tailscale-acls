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

#### Making the fix self-completing

When the bot pushes the formatted commit with `GITHUB_TOKEN`, GitHub *does* create
a `pull_request` run for it — but holds it in an **approval-required** state, so the
`acls` check stays stale until someone with write access clicks **Approve and run**
on the PR's checks. (Re-running the old failed check is not a substitute: a re-run
reuses the commit that triggered the original run, i.e. the unformatted one.)

A GitHub App's push is not held for approval, so configuring one makes the fix
self-completing, with no approval click. `lint-fix.yml` picks this up
automatically: if `FMT_APP_ID` and `FMT_APP_PRIVATE_KEY` are both set it mints an
installation token and pushes with that, and otherwise it falls back to the
approval flow above. Nothing to change in the workflow either way.

To set it up:

1. **Org Settings → Developer settings → GitHub Apps → New GitHub App.** Own it at
   the org, not personally, so it outlives whoever made it.
2. Name it something like `Comet ACL Formatter`, set the homepage to this repo, and
   **uncheck Webhook → Active** — it receives nothing.
3. Under **Repository permissions**, grant **Contents: Read and write**. Nothing
   else: the workflow still uses `GITHUB_TOKEN` for comments and PR reads, so the
   app only needs to push.
4. Set **Where can this app be installed** to *Only on this account*, then create it.
5. Note the **App ID**, and **Generate a private key** (downloads a `.pem`).
6. **Install** the app, choosing *Only select repositories* → this repo.
7. Add two repo secrets: `FMT_APP_ID` (the app ID) and `FMT_APP_PRIVATE_KEY` (the
   whole `.pem`, `-----BEGIN` line and all).

Step 6 is the one that's easy to skip — creating an app doesn't install it, and
without an installation on this repo the token request returns `404` (a bad key
returns `401`, so the two are easy to tell apart). Either way the formatter keeps
working: if the token can't be minted, the push falls back to `GITHUB_TOKEN` and
the approval click comes back.

Installation tokens are short-lived (an hour), but the private key is durable — it's
the one credential in this repo that needs rotating, and it only grants
`contents:write` on this repo. Rotate it by generating a new key, replacing the
secret, then deleting the old key in the app's settings.

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

