# Comparison exercises

Always pick one or two exercises that seem the most helpful at this point of the exploration.

Take great care to present the results visually, using all the tools available in your output format.

## Discriminator table

This is a great way to introduce a new set of candidates.

Options as columns, dimensions as rows, and drop every row where all options score the same.

Keep estimates relative (small/medium/large, or ranked) unless you have grounds for a number. Absolute days and dollar amounts look precise and are usually invented.

```
                  A: Patch        B: Refactor     C: Delegate
Effort            small           medium          large
Reversibility     easy            easy            one-way (data)
Blast radius      1 module        4 modules       auth path + db
Next change       harder          easier          easier
Ongoing cost      +1 quirk        neutral         vendor fee, vendor

Same for all: correctness, p99 latency, API compat, security review.
```


## Signed scale when cells are ordinal

```
                    A     B     C
Ship speed         ++     o    --
Maintainability     -     +    ++
Safety              +     o     ?
Simplicity         ++     +    --
```

Fixed-width, no legend needed beyond "+ is good", and polarity is uniform so a column of pluses reads as a good option at a glance. Always phrase rows so more-is-better: "safety" rather than "regression risk", "simplicity" rather than "cognitive load". A `?` marks an unknown; see "Cheapest experiment" for how to resolve it.

Bars work too and carry magnitude better, but only for genuinely ordinal things:

```
Ship speed    A ████░  B ██░░░  C █░░░░
```

## Conditional recommendations

Inverts the frame from "here are options, you rank them" to "here is the rule". This is often better than recommending one absolute winner: you're deriving decision boundaries.

```
→ A if the deadline is real and you accept revisiting in Q3.
→ B if session.rb is already on someone's plate.
→ C only if you're also retiring the legacy session store.
```

## ASCII quadrant on the two crux dimensions

```
        reversible
             │
    A        │
             │   B
   ──────────┼──────────  effort
             │
             │        C
             │
       one-way
```

Worth it only when the two dimensions genuinely dominate, but it shows dominance and the Pareto frontier in a way tables don't.

## Phase bars for incrementality

Shows the thing a single effort number hides: when value arrives, and whether there's a long unglamorous tail after the "done" moment.

```
A  ▓▓                     value lands day 2
B  ░░░░▓▓▓▓▓▓             spike, then ships whole
C  ░░░░▓▓▓▓▓▓░░░░░░▓▓     ships, then 3w migration tail
```

## Trade-offs

Useful when only a few candidates are left in the table.
A large table would produce too many pairs.

One block per pair. The reverse direction is the mirror image and adds nothing.

```
### B over A

Costs:
- larger change
- introduces a new abstraction
- migration with a high regression surface

Buys:
+ removes two existing special cases
+ cleaner ownership
+ likely follow-up requirement becomes straightforward
```

## Stakeholder walkthrough

Make multiple personas answer concrete questions for each solution, e.g.:

- **End user:** What gets easier? What becomes surprising? What failure would I notice?
- **Product owner:** Which requirements become easy/hard to change?
- **Developer:** What do I need to understand before modifying this?
- **Operator/support:** What happens when it breaks at 03:00?
- **Security/privacy:** What new trust boundaries or sensitive states exist?
- **Finance/management:** What ongoing cost or dependency did we take on?

The trick is to role-play incentives and tasks, not personalities.


## The next three requirements

Invent plausible follow-up requests and mentally implement them against every candidate.

For example:

> Current requirement: support one additional approval state.

Then test:

> Next quarter: approvals can expire.
> Later: different customers have different approval policies.
> Later: administrators need to override approval.

For each solution ask:

> Does this extension fit naturally, require another special case, or force us to undo today's design?

This is probably one of the strongest exercises for judging abstraction quality.


## Pre-mortem

Assume:

> We chose this solution. Six months later everyone agrees it was a mistake.

Then ask:

> What most plausibly happened?

For example:

```
Solution A failed because every follow-up feature added another conditional.
Solution B failed because the abstraction turned out to have only one real use case.
Solution C failed because migration complexity consumed far more effort than expected.
```

This is much better than generic "risks" because you're forced to construct a believable failure story.

Pairs well with the success-mortem.


## Success-mortem

Imagine it's six months later and this solution turned out to be an unusually good decision. Why?

This is a good exercise to prevent risk analysis from systematically favoring conservative solutions.

Example results could be:

```
A succeeded because requirements stabilized and we never needed more abstraction.
B succeeded because three later features all fit the new policy model.
C succeeded because removing the old subsystem eliminated an entire category of bugs.
```

Now you're comparing the worlds in which each solution wins.

## Regret minimization

Ask of each choice:

> If this turns out to be wrong, how much do we regret it?

You get very different shapes:

```
A: Cheap to try; mildly painful if requirements grow.
B: Moderate upfront cost; moderate downside.
C: Expensive commitment; excellent if our architectural hypothesis is right.
```

This surfaces optionality.

Sometimes the technically inferior solution is rational because it keeps future choices open.

## Explain it to the next developer

Imagine someone joins the project a year later.

In three sentences:

> Explain why this system works this way and where they need to make changes.

Compare:

```
A: "When X happens, we special-case it here because..."
B: "All authorization decisions go through policies..."
C: "We model the workflow explicitly as state transitions..."
```

If you need five historical anecdotes to explain a design, that's information.

This isn't simply "simplicity"; it tests conceptual integrity.

## Steelman each solution

Make the strongest credible case for every candidate, including the ugly-looking one.

Assume a very competent engineer deliberately chose this. Why might they be right?

This guards against generating a rigged spectrum like:

```
A: horrible hack
B: reasonable compromise
C: elegant architecture ♥
```

which is a real danger with the minimum/maximum spectrum generator.

Steelmanning pairs well with "Conditional recommendations" above: once you know the world in which each candidate wins, state it as a rule.

## Cheapest experiment

For uncertain trade-offs:

> What's the cheapest thing we could do to learn whether this concern is real?

Examples:

- prototype the library integration,
- benchmark the query,
- inspect five existing analogous cases,
- spike the migration,
- implement only the new abstraction interface,
- test the external API's weird edge case.

Then:

```
Uncertainty: Will library X fit our auth model?
Experiment: Integrate one login flow without migration.
Cost: ~small
Decision affected: Build vs integrate.
```

This changes the exercise from guessing accurately to reducing uncertainty cheaply, which is often the better engineering move.
