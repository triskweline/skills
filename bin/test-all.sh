#!/usr/bin/env bash
#
# Run every test suite in the repository: the repo-wide ones under tests/, and
# each skill's own suite under skills/<name>/tests/. Suites are discovered
# rather than listed, so a new skill's tests are picked up without editing this
# script or the CI workflow.
#
# This is the single entry point used both locally and by CI, so that "it passes
# on my machine" and "it passes on the runner" mean the same command. It needs
# nothing but python3, git and bash -- no pip install, no version manager.
#
# Usage:
#   bin/test-all.sh            # run everything
#   PYTHON=python3.12 bin/test-all.sh   # run against a specific interpreter
#
set -uo pipefail

# Resolve the repo root (parent of this script's bin/ directory), following
# symlinks so the script works even when invoked through a symlinked path.
script_path="${BASH_SOURCE[0]}"
while [ -L "$script_path" ]; do
  script_path="$(readlink "$script_path")"
done
bin_dir="$(cd "$(dirname "$script_path")" && pwd)"
repo_root="$(cd "$bin_dir/.." && pwd)"

python="${PYTHON:-python3}"

echo "Running the test suites with $("$python" -V 2>&1) at $python"
echo

failed=()
ran=0

# Run one suite, from a working directory of the caller's choosing. A skill's
# suite runs from the skill directory, which is how its own docs invoke it.
run_suite() {
  local label="$1" workdir="$2" script="$3"
  echo "--- $label"
  if (cd "$workdir" && "$python" "$script"); then
    echo "--- $label: OK"
  else
    echo "--- $label: FAILED" >&2
    failed+=("$label")
  fi
  ran=$((ran + 1))
  echo
}

# Repo-wide suites.
for suite in "$repo_root"/tests/test_*.py; do
  [ -f "$suite" ] || continue
  run_suite "$(basename "$suite")" "$repo_root" "$suite"
done

# Each skill's own suite.
for suite in "$repo_root"/skills/*/tests/test_*.py; do
  [ -f "$suite" ] || continue
  skill_dir="$(dirname "$(dirname "$suite")")"
  run_suite "$(basename "$skill_dir")/$(basename "$suite")" \
            "$skill_dir" "$suite"
done

if [ "$ran" -eq 0 ]; then
  echo "No test suites found -- expected tests/test_*.py or skills/*/tests/test_*.py" >&2
  exit 1
fi

if [ "${#failed[@]}" -gt 0 ]; then
  echo "FAILED: ${#failed[@]} of $ran suite(s): ${failed[*]}" >&2
  exit 1
fi

echo "All $ran suite(s) passed."
