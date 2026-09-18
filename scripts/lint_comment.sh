#!/usr/bin/env bash
# Post (or rewrite) the single lint-report comment on a pull request.
#
# There is at most one of these per PR: we find it by the HTML marker below and
# PATCH it, so a branch that gets pushed ten times doesn't leave ten comments.
#
# When the lint fails the comment carries an unchecked task-list box. GitHub has
# no workflow trigger for emoji reactions, but ticking a box on a comment is an
# `issue_comment: edited` event, so that box is what lint-fix.yml listens for --
# one click, same as a reaction would have been.
#
# Expects, in the environment: GH_TOKEN REPO PR LINT_OUTPUT LINT_CODE SHA
# RUN_URL SAME_REPO
set -euo pipefail

MARKER='<!-- acl-lint-report -->'
CHECKBOX='- [ ] **Format it for me.** Tick this box (or comment `/fmt`) to run the formatter and commit the result to this branch.'
# Ticking the box needs write access, because the workflow behind it pushes a
# commit. In practice that excludes nobody who could have opened a same-repo PR
# -- creating the branch needed write access too -- but say so rather than
# letting someone click a box that silently refuses them.
NEEDS_WRITE='<sub>Requires write access, since it pushes a commit. Without it, run `python3 scripts/fmt_policy.py` locally and push the result.</sub>'
BODY="$(mktemp)"
MAX_LINES=120

{
  echo "$MARKER"
  if [ "${LINT_CODE}" = "0" ]; then
    echo "### ✅ Policy lint passed"
    echo
    echo "\`policy.hujson\` parses and every group member is on its own line."
  else
    echo "### ❌ Policy lint failed"
    echo
    echo "\`scripts/fmt_policy.py --check\` rejected \`policy.hujson\`."
    echo
    if [ "${SAME_REPO}" = "true" ]; then
      echo "$CHECKBOX"
      echo
      echo "$NEEDS_WRITE"
    else
      echo "> This PR comes from a fork, so the fix can't be pushed for you."
      echo "> Run \`python3 scripts/fmt_policy.py\` locally and push the result."
    fi
    echo
  fi
  echo
  echo '<details><summary>Lint output</summary>'
  echo
  echo '```'
  printf '%s\n' "${LINT_OUTPUT}" | head -n "$MAX_LINES"
  if [ "$(printf '%s\n' "${LINT_OUTPUT}" | wc -l)" -gt "$MAX_LINES" ]; then
    echo "... truncated, see the full log in the run."
  fi
  echo '```'
  echo
  echo '</details>'
  echo
  echo "<sub>\`${SHA:0:7}\` · [run log](${RUN_URL})</sub>"
} > "$BODY"

existing="$(gh api --paginate "repos/${REPO}/issues/${PR}/comments" \
  --jq "[.[] | select(.body | contains(\"${MARKER}\")) | .id] | first // empty")"

payload="$(jq -n --rawfile body "$BODY" '{body: $body}')"

if [ -n "$existing" ]; then
  printf '%s' "$payload" |
    gh api --method PATCH "repos/${REPO}/issues/comments/${existing}" --input - --silent
  echo "updated comment ${existing}"
else
  printf '%s' "$payload" |
    gh api --method POST "repos/${REPO}/issues/${PR}/comments" --input - --silent
  echo "posted a new comment"
fi

# The comment is the report; the job's own status is what gates `acls`.
exit "${LINT_CODE}"
