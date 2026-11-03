## DRADIS

The dradis file lists what waits for the user in this session; the dradis plugin shows it in the
user's status line. The agent keeps it at `~/.claude/dradis/$CLAUDE_CODE_SESSION_ID.txt`, written
with a Bash command so the variable expands. One item per line: `<state> <slug>`, optionally
` - short note`. The slug is the kebab-case name used in the conversation and stays the same
while the item is open.

- `now`: the user's turn, to answer the agent or to do a task.
- `later`: queued behind `now`, not started.

Before ending a turn, the agent checks that the dradis file lists exactly what waits for the user;
if not, rewriting the whole file is its last tool call. The user waits whenever the agent
can't go on without an answer, a choice (even with a recommendation), an approved draft or a
task only the user can do. Answered, done or dropped items leave; the agent's own to-dos never
go in. The agent asks one thing at a time. After a context compaction, it reads the file
before rewriting it. Subagents never write it. The agent updates the file silently: its replies
never mention the dradis file or changes to it, because the user sees them in the status line.
