#!/usr/bin/env bash
#
# Symlink every skill under skills/* into ~/.claude/skills/ so they are
# available in all Claude Code sessions.
#
# Usage:
#   bin/link-all.sh            # link into ~/.claude/skills
#   SKILLS_DIR=/path bin/link-all.sh   # link into a custom skills directory
#
set -euo pipefail

# Resolve the repo root (parent of this script's bin/ directory), following
# symlinks so the script works even when invoked through a symlinked path.
script_path="${BASH_SOURCE[0]}"
while [ -L "$script_path" ]; do
  script_path="$(readlink "$script_path")"
done
bin_dir="$(cd "$(dirname "$script_path")" && pwd)"
repo_root="$(cd "$bin_dir/.." && pwd)"

source_dir="$repo_root/skills"
skills_dir="${SKILLS_DIR:-$HOME/.claude/skills}"

if [ ! -d "$source_dir" ]; then
  echo "Error: source directory not found: $source_dir" >&2
  exit 1
fi

mkdir -p "$skills_dir"

linked=0
for skill_path in "$source_dir"/*/; do
  [ -d "$skill_path" ] || continue
  skill_path="${skill_path%/}"
  name="$(basename "$skill_path")"
  target="$skills_dir/$name"

  # Skip anything that already points at the right place.
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill_path" ]; then
    echo "= $name (already linked)"
    continue
  fi

  # Refuse to clobber a real directory or file that isn't our symlink.
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "! $name (skipped: $target exists and is not a symlink)" >&2
    continue
  fi

  ln -sfn "$skill_path" "$target"
  echo "+ $name -> $skill_path"
  linked=$((linked + 1))
done

echo "Done. Linked/updated $linked skill(s) into $skills_dir"
