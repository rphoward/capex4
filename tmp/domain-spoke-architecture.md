# Domain-Spoke Architecture

Status: reusable architecture instruction

## Purpose

Use this document to plan and review small or medium software projects built
with coding agents. It is project-agnostic. Project-specific terms appear only
inside sections labeled `Example`.

This document is not inspiration. It is a rule set. A planner that uses this
architecture must produce slices that preserve ownership, naming, dependency
direction, and proof.

## Definition

Domain-spoke architecture is a domain-centered, AI-legible, proof-driven
architecture.

It uses:

- Domain-Driven Design for language discipline.
- Clean Architecture for dependency direction.
- Screaming Architecture for intent-revealing names.
- Vertical slices for delivery rhythm.
- Ports and adapters for infrastructure.
- Presentation transforms for UI, HTTP, CLI, document, or API surfaces.
- Phase and slice records for planning and review.

The domain center protects durable meaning. Spokes express user and system
capabilities. Infrastructure supplies concrete outside mechanisms through
ports. Presentation renders clean outputs from the application boundary.

## Core Rule

```text
Planning a slice does not grant permission to bypass architecture.
```

A slice may cross layers. A slice must not change ownership silently. If a
slice changes ownership, source data, dependency direction, or stack direction,
the planner must create an architecture decision slice before implementation.

The exact conditions and router state that require an architecture decision
slice are defined in the unified contract
(`codex-router-planner-unified.md`).

## Shape

```text
                         presentation
                    routes / forms / views
                               ^
                               |
                      presentation transform
                               ^
                               |
domain center <- application use case / spoke -> ports
                               |
                               v
                 orthogonal infrastructure adapters
```

## Required Vocabulary

Domain center:
The inner code that owns durable business meaning, human-facing policy,
invariants, and product language.

Spoke:
A cohesive user or system capability that grows outward from the domain center
through application, ports, infrastructure, and presentation.

Orthogonal infrastructure:
Concrete adapters that provide outside capabilities. Infrastructure is not a
feature. It is a field of mechanisms that plug into spokes through ports.

Presentation transform:
The adapter that turns application/domain output into UI, HTTP, CLI, document,
message, or API-specific shape.

AI-legible semantic architecture:
An architecture whose folder and module names let humans and coding agents infer
meaning, intent, function, and contents accurately before opening files.

## DDD Rules

Apply Domain-Driven Design this way:

- Use the product's real language in folders, modules, public functions, tests,
  and records.
- Make important domain concepts physically visible in code.
- Put invariants and behavior policies in the domain center.
- Treat outside source models as foreign models.
- Translate outside source models through an anti-corruption boundary.
- Encode product values as named policies when those values affect behavior.

Do not:

- add tactical DDD ceremony without pressure;
- create aggregates, repositories, events, or context maps by default;
- hide domain meaning inside framework routes, templates, database models, or
  browser state;
- use generic names when domain names exist.

Universal rule:

```text
Do not add entities everywhere.
Make the product's real concepts physically visible and protected.
```

Example:

```text
For a rental investment app, example concepts are deal_viability,
repair_reserve_plan, financing_terms, and cash_flow_explanation.

For a scheduling app, example concepts are availability_window,
booking_request, calendar_conflict, and reminder_policy.
```

## Clean Architecture Rules

Apply Clean Architecture this way:

- Dependencies point inward.
- Domain does not import application, infrastructure, presentation, framework,
  transport, database, browser, queue, vendor SDK, or deployment code.
- Application use cases orchestrate intent and call the domain.
- Application uses ports for outside capabilities.
- Infrastructure implements ports.
- Presentation translates transport/user input into application requests and
  renders application outputs.
- Bootstrap wires concrete adapters to use cases.

Do not:

- force a four-ring package structure when fewer modules communicate better;
- create a repository layer before persistence pressure exists;
- create a service layer that only hides vague procedural code;
- create class-heavy interfaces when a small typed module or protocol is enough;
- let framework and transport details become business truth.

Universal rule:

```text
Every feature does not need to look like a Clean Architecture diagram.
Every feature must protect business truth from framework and transport details.
```

## Screaming Architecture Rules

Apply Screaming Architecture this way:

- A directory scan must reveal what the app does.
- Top-level names must communicate product purpose.
- Framework folders must not be the app's main story.
- Feature spokes must be named after user intent or domain capability.
- Layer names are allowed, but layer names alone are insufficient.

Good universal names:

```text
evaluate_request
create_booking
solve_threshold_question
explain_result
apply_override
load_source_model
build_decision_packet
render_confirmation
```

Forbidden weak names unless qualified by domain role:

```text
helpers
utils
services
manager
processor
adapter
handler
common
misc
```

Qualified technical names are allowed:

```text
booking_request_form
calendar_provider_adapter
payment_receipt_view_model
source_model_mapper
threshold_question_route
```

## Vertical Slice Rules

Apply vertical slices this way:

- A slice delivers one user or system capability.
- A slice states which spoke it touches.
- A slice states which layer owns each new concept.
- A slice defines proof before implementation.
- A slice may touch multiple layers only when each layer keeps its role.

Do not:

- duplicate shared domain truth inside a feature folder;
- let feature cohesion defeat source-data ownership;
- hide architecture decisions inside implementation slices;
- name slices with vague maintenance language.

Good slice names:

```text
Map source model ownership
Add evaluate-request application boundary
Render result explanation fragment from view model
Prove route does not bypass use case
```

Forbidden slice names:

```text
Clean up architecture
Refactor app
Modernize frontend
Improve domain
Move to new stack
```

## Presentation Rules

Presentation translates. Presentation does not own domain meaning.

Presentation may own:

- routes;
- form parsing;
- transport validation;
- view models;
- templates;
- fragments;
- browser-only gestures;
- formatting;
- response serialization.

Presentation must not own:

- domain invariants;
- source model meaning;
- business policy;
- calculation policy;
- durable workflow semantics;
- application use-case decisions;
- trust or teaching policy unless explicitly modeled as presentation-only copy.

Preferred request flow:

```text
request
  -> route parses transport shape
  -> application request
  -> use case
  -> domain behavior
  -> result / receipt / view model
  -> presentation output
```

For server-rendered or HTMX apps:

```text
HTMX request
  -> route parses form
  -> application request dataclass or gate model
  -> use case
  -> domain behavior
  -> view model
  -> template fragment
  -> HTMX swaps HTML
```

Do not:

```text
HTMX request
  -> route mutates browser-shaped state
  -> template invents domain meaning
  -> JavaScript patches missing application behavior
```

## Infrastructure Rules

Infrastructure provides outside mechanisms. Infrastructure does not own policy.

Infrastructure may own:

- database adapters;
- file adapters;
- source model readers;
- API clients;
- vendor SDK wrappers;
- cache adapters;
- queue adapters;
- email adapters;
- export adapters;
- local filesystem details.

Infrastructure must not own:

- use-case orchestration;
- domain invariants;
- presentation flow;
- user intent;
- product language that belongs in the domain center.

Infrastructure names must include mechanism and domain role:

```text
json_source_model_store
postgres_booking_repository
stripe_payment_adapter
filesystem_report_exporter
```

## Folder Schema

Use this structure when a project has enough pressure for explicit folders:

```text
src/<app_name>/
  domain/
    <core_concept>/
    <policy_area>/
    <source_model_name>/

  application/
    <capability_spoke>/
      request.*
      result.*
      use_case.*

  ports/
    <needed_outside_capability>.*

  infrastructure/
    <concrete_adapter_for_port>/

  presentation/
    <transport_or_surface>/
      <capability_spoke>/
        route_or_controller.*
        form_or_parser.*
        view_model.*
        templates_or_fragments/

  bootstrap.*
```

Use this structure when the app is still small:

```text
src/<app_name>/
  domain/
  application/
    <capability_spoke>.*
  infrastructure/
  presentation/
  bootstrap.*
```

Do not create empty architecture folders. Add a folder only when it owns real
code, data, records, or tests.

## Architecture Records

Use pseudo-Lisp records. They match planner artifacts, keep labels explicit, and
remove YAML indentation ambiguity.

Promote a record to a strict parser or typed schema only after repeated use
proves the fields are stable.

### Project Architecture Record

```lisp
(architecture
  (name "<project architecture name>")
  (status draft | active_contract | reference)
  (domain_center
    (purpose "<durable business meaning the center protects>")
    (owns
      "<domain concept>")
    (must_not_own
      "<outer mechanism>"))
  (primary_spokes
    (spoke
      (name "<capability name>")
      (user_intent "<user/system outcome this spoke serves>")
      (owner_layer application)
      (domain_concepts
        "<concept>")
      (presentation_surfaces
        "<route/page/fragment/API>")
      (infrastructure_ports
        "<port or outside need>")))
  (orthogonal_infrastructure
    (adapter_family
      (name "<adapter family>")
      (provides "<outside capability>")
      (plugged_into
        "<port or use case>")))
  (presentation_style
    (primary server_rendered | api | cli | spa | document | mixed)
    (browser_javascript_policy "<minimal/enhancement/allowed scope>"))
  (architecture_tests
    "<ownership proof>"))
```

### Spoke Record

```lisp
(spoke
  (name "<capability_spoke>")
  (status planned | active | implemented | retired)
  (intent "<user or system outcome>")
  (owns
    (domain
      "<concept or policy owned/used by this spoke>")
    (application
      "<request/result/use case>")
    (presentation
      "<view model/route/fragment>")
    (infrastructure
      "<adapter only if this spoke needs a concrete outside mechanism>"))
  (forbidden_ownership
    "<concept this spoke must not own>")
  (entrypoints
    "<HTTP route, CLI command, job, event, etc.>")
  (proof
    "<test or manual proof>"))
```

### Phase Record

```lisp
(phase
  (name "<phase name>")
  (status draft | planned | active | complete | deferred)
  (finish_line "<observable ending condition>")
  (done_proof
    "<proof that closes the phase>")
  (allowed_write_surface
    "<path or subsystem>")
  (deferred_outcomes
    "<explicitly not now>")
  (constraints
    "planning does not grant permission to bypass architecture"))
```

### Slice Record

```lisp
(slice
  (name "<slice name>")
  (phase "<phase name>")
  (status planned | active | review_needed | passed | failed | deferred)
  (intent "<one capability, boundary, or risk>")
  (touched_spokes
    "<spoke name>")
  (layer_ownership
    (domain
      (owns
        "<meaning added or protected>")
      (must_not_change
        "<domain boundary not in scope>"))
    (application
      (owns
        "<use case/request/result behavior>"))
    (infrastructure
      (owns
        "<adapter/source loading behavior>"))
    (presentation
      (owns
        "<route/view/fragment behavior>")))
  (allowed_edits
    "<path>")
  (forbidden_edits
    "<path or behavior>")
  (architecture_guardrails
    "<specific rule this slice must preserve>")
  (proof
    "<test command or manual proof>")
  (review_question "<review decision to make>"))
```

### Architecture Decision Slice

```lisp
(architecture_decision_slice
  (question "<decision to resolve>")
  (current_owner "<current layer/spoke>")
  (proposed_owner "<new layer/spoke>")
  (reason_for_change "<pressure or evidence>")
  (rejected_options
    (option
      (name "<option>")
      (reason "<why not>")))
  (proof_to_accept
    "<test/doc/path proof>")
  (implementation_allowed false))
```

An architecture decision slice is planning-only. Implementation requires a
separate human-approved implementation slice.

## Planner Contract

A planner using this architecture must do this before writing a slice:

1. Identify the domain concept or user capability.
2. Select an existing spoke or propose a new spoke.
3. State layer ownership for each part of the change.
4. Name the adapters allowed to translate data.
5. Name the architecture rules the slice must preserve.
6. Define proof before implementation.
7. Mark out-of-scope temptations explicitly.

The planner may propose a slice that crosses layers. The planner must not
propose a slice that changes ownership silently.

If ownership is unclear, the planner must create an architecture decision slice.

## Naming Rules

Names must reveal at least one of:

- domain object;
- user intent;
- business policy;
- transformation role;
- source boundary;
- trust or proof role;
- phase or slice purpose.

Names must not reveal only:

- file type;
- framework role;
- vague reuse;
- implementation detail without domain role.

Naming test:

```text
Can a capable developer or AI agent guess what belongs here without opening
the file?
```

If the answer is no, rename the module or add a nearby architecture record.

## Architecture Test Rules

Architecture tests must prove ownership:

- domain imports no presentation, infrastructure, framework, or templates;
- application use cases do not import concrete infrastructure;
- infrastructure implements ports and does not own policy;
- presentation calls use cases and renders view models;
- templates and fragments do not calculate domain values;
- runtime source data is not loaded from test fixtures;
- each spoke has focused tests at the application boundary;
- planner records include owner, allowed edits, forbidden edits, and proof.

## Anti-Patterns

Reject:

- architecture by documentation only;
- feature folders that duplicate shared domain truth;
- generic service/helper/manager modules;
- browser or template code owning domain meaning;
- infrastructure source shape leaking into domain language;
- planner slices named "refactor architecture" or "clean up domain";
- implementation slices without proof;
- stack migration disguised as cleanup;
- strict schemas before the workflow stabilizes.

## Migration Path From A Messy App

1. Classify current docs as `contract`, `draft`, or `reference`.
2. Create a project architecture record.
3. Identify the current domain center.
4. List current spokes by user or system capability.
5. Mark places where presentation or infrastructure owns domain meaning.
6. Add one architecture test for the most dangerous drift.
7. Plan one slice that moves one concept to its correct owner.
8. Prove the slice.
9. Repeat.

Do not start with a total folder rewrite. Start by making one concept physically
owned, named, and proven.
