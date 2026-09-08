# Solution generators

Below you can find a number of strategies to come up with new ideas for possible solutions or approaches.

Do not mechanically produce one solution for every generator. Inspect the problem and repository, choose the generators that expose genuinely different approaches. Stop when additional candidates are merely similar permutations of existing ideas.

## Keep solutions realistic

A generated solution stands for an archetype of an approach, but it must still be a realistic, workable change to this repository. Don't present extreme strawman parodies that the human has no choice but to kill. E.g. the maximum solution from the Porzio Spectrum may contain heavy and risky changes to the code, but should not suggest rewriting the entire codebase in a new programming language because it is faster.

If you judge a generated solution to be too extreme or impracticable, check if you can make it workable by limiting its scope or balancing it out with aspects from other approaches. In the example above, instead of rewriting the entire application in a faster language, suggest only porting a small but performance-critical component and integrating that.

## Generator: Your own intuition

As an experienced coding agent you already have some intuition for ways to implement the requirement.

Describe the solution you would build if the human asked you to one-shot the implementation without further instructions.

## Generator: The Porzio Spectrum

This is [Caleb Porzio](https://calebporzio.com/)'s "deconstructed PR" idea.

The spectrum has three poles. Propose the ones that are realistic here:

- Define a minimum, patchy solution to get by, with minimum blast radius but potentially incomplete scope or poorly written code.
- Define a maximum, pure and fundamental solution that solves the problem in the most complete way, restructuring other parts of the system if need be, to create a harmonious and thorough new world.
- Define an "evaporate the problem" solution, where some other part of the world is reconstructed so this problem doesn't happen in the first place.

Don't talk to the human about "the Porzio Spectrum", it will mean nothing to them.

## Generator: Move it in the stack

Generate solutions that deliberately move the responsibility across existing architectural boundaries. Consider caller vs callee, client vs server, application vs database, producer vs consumer, and this system vs an external system.

Ask at which layer the problem is cheapest to solve: database constraint, ORM/model, service, controller, client, edge/proxy, build pipeline, infrastructure config. The same requirement often has a 200-line solution at one layer and a 3-line one two layers down. Uniqueness enforced in application code vs a unique index is the canonical example.

## Generator: Move it in time

When does the work happen: build time, deploy time, first request, every request, or a background job? Precompute vs compute on demand, code generation vs runtime reflection, eager migration vs lazy backfill on read. This axis is nearly orthogonal to everything else and usually produces at least one surprising option.

## Generator: Relax a requirement

Treat each stated requirement as negotiable and ask which one is carrying the cost. Ask what happens if you deliberately relax the semantics.
"Must be real-time" vs "within a minute" are different systems. "Must work for all existing records" vs "for records created from now on" too. The output here is a solution plus the conversation you'd need to have to unlock it, which is a legitimate engineering option and one developers systematically skip.

For example, "We need the dashboard to show the current count" could mean either:

- Transactionally exact.
- Eventually consistent.
- Snapshot from last refresh.
- Approximate.
- Exact only after explicit refresh.

This is valuable because requirements often accidentally imply guarantees far stronger than users actually need.

## Generator: Local precedent

Find where this repo already solved a structurally similar problem and propose the consistent version of that.

## Generator: Happy-path sophistication vs recovery sophistication

Instead of making the primary mechanism more intelligent, make failure cheap.

Suppose matching external records is difficult:

- Build a sophisticated matching algorithm.
- Use simple matching + flag ambiguity.
- Simple matching + admin correction UI.
- Import everything and provide reconciliation afterwards.

This is one of the strongest engineering moves:

> What if we made the common case extremely simple and invested in a good escape hatch?

It often beats clever automation.

## Generator: Change the abstraction level

The abstraction level has three poles. Propose the ones that are realistic here:

- Special case: implement exactly this requirement.
- Shared mechanism: identify 2–3 existing similar cases and introduce a reusable abstraction.
- General capability: model the underlying concept explicitly so this and plausible future requirements become configuration/data.

For example, "admins may edit locked invoices":

- Add `|| user.admin?`.
- Introduce a reusable authorization predicate.
- Introduce a policy/permission model.

Importantly, none is automatically superior. The general capability may be absurd overengineering if there's only one case.

## Generator: Build or buy

For example: The human wants to implement OAuth authentication. There are many levels of how much of this we build ourselves, for example:

- Build it ourselves in the repo. Lots of new code to build and maintain. Easy to bridge with existing code and maximum flexibility for future requirements.
- Integrate an existing OAuth library that provides the necessary routing and crypto. Will probably have some friction with existing auth code.
- Delegate authentication to an external service that already supports OAuth. Probably means replacing the entire existing auth system and a painful data migration, but reduces the amount of code we need to maintain in the future.
- Fork/vendor an existing library in and patch it. Then either maintain the entire thing or try to get your change merged upstream.
