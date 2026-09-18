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

If the check fails, the bot's comment on your PR has a **"Format it for me"**
checkbox — tick it, or comment `/fmt`, and it'll run the formatter and commit the
fix to your branch.
