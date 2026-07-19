#!/usr/bin/env bash
#
# Sync every skill under skills/* into ~/.claude/skills/ so they are
# available in all Claude Code sessions. This mirrors the repo: it links
# current skills AND prunes stale links for skills that were renamed or
# removed. Only symlinks that point back into this repo's skills/ directory
# are ever removed; unrelated files and links are left untouched.
#
# Usage:
#   bin/link-all.sh            # sync into ~/.claude/skills
#   SKILLS_DIR=/path bin/link-all.sh   # sync into a custom skills directory
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

# Prune stale links: any symlink in the skills dir that points back into this
# repo's skills/ directory but no longer resolves (skill renamed or removed).
# We deliberately only touch links whose target is inside our source_dir, so
# links to other skill repos or unrelated files are never removed.
pruned=0
for target in "$skills_dir"/*; do
  # Guard against the glob matching nothing (no entries in the dir).
  [ -e "$target" ] || [ -L "$target" ] || continue
  [ -L "$target" ] || continue

  link_target="$(readlink "$target")"
  case "$link_target" in
    "$source_dir"/*) ;;   # points into our repo — a candidate for pruning
    *) continue ;;        # points elsewhere — leave it alone
  esac

  # Keep it if it still resolves to an existing skill directory.
  [ -d "$target" ] && continue

  rm -f "$target"
  echo "- $(basename "$target") (pruned: $link_target no longer exists)"
  pruned=$((pruned + 1))
done

echo "Done. Linked/updated $linked skill(s), pruned $pruned stale link(s) in $skills_dir"
