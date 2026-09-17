# tailscale-acls

Tailnet policy file (ACLs) for the `comet-robotics.org.github` tailnet, managed via GitOps.

**The admin console is not the source of truth — this repo is.** Editing ACLs in the
Tailscale admin console is disabled; changes must go through a pull request here.

## How to change ACLs

1. Open a PR against `main` editing [`policy.hujson`](policy.hujson).
2. CI runs `action: test`, which validates the syntax and runs any `tests` blocks
   against the live tailnet. A red check means the policy is invalid — do not merge.
3. Get a review, then merge. CI runs `action: apply` on `main`, which pushes the
   policy to the tailnet.

## Authentication

CI authenticates with **OIDC federated identity** — there are no long-lived secrets
and nothing to rotate. Two Tailscale trust credentials are used, deliberately split:

| Secret | Trust credential subject | Scopes | Used by |
|---|---|---|---|
| `TS_OAUTH_ID_TEST` / `TS_AUDIENCE_TEST` | `repo:Comet-Robotics/tailscale-acls:pull_request` | `policy_file` read | PR `test` |
| `TS_OAUTH_ID_APPLY` / `TS_AUDIENCE_APPLY` | `repo:Comet-Robotics/tailscale-acls:ref:refs/heads/main` | `policy_file` read+write | `main` `apply` |

The split matters: because the write credential's subject is pinned to
`refs/heads/main`, a pull request cannot apply ACLs **even if the PR edits the
workflow file**. A single credential would not give you that.

`TS_TAILNET` is `comet-robotics.org.github`.

Trust credentials live in the admin console under
Settings → [Trust credentials](https://console.tailscale.com/admin/settings/trust-credentials).

## Notes

- `policy.hujson` is HuJSON (JSON with comments and trailing commas). Keep the comments.
- Group membership is driven by GitHub identities (`user@github`), since this tailnet
  uses GitHub as its identity provider.
