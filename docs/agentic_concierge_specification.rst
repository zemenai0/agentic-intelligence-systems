HabitaLife Digital Concierge: End-to-End Architecture Specification
===================================================================

Purpose Of This Document
------------------------
This document defines the end-to-end architecture for the HabitaLife Digital
Concierge. It is a full engineering, product, and operations specification that can guide design,
implementation, and review.

The specification is grounded in two existing source documents:

* The HabitaLife PRD, which defines the problem statement, target users, and
  MVP value proposition.
* The initial system design document, which establishes the modular monolith,
  FastAPI, PostgreSQL, JWT/RBAC, room lifecycle, reservation flows, and guest
  service workflows.

This specification intentionally goes beyond the current MVP. It describes both
the baseline system we can build now and the future-ready extensions that make
HabitaLife an agentic hospitality platform rather than a simple chat assistant.

Document Conventions
--------------------
Two scope markers are used throughout this specification:

* ``MVP baseline`` means directly aligned with the current PRD and system
  design.
* ``Future-ready extension`` means a planned or optional capability that extends
  the same architecture without contradicting the current baseline.

Product Context And Operating Reality
-------------------------------------
HabitaLife exists because resorts in Ethiopia and similar markets need a better
guest experience without depending on expensive smart-room infrastructure. The
core problem is not only guest communication; it is the absence of a shared
operational brain that understands guest intent, coordinates staff, tracks room
state, detects dissatisfaction early, and improves service quality over time.

The system must operate under real hospitality constraints:

* Guests expect fast, personalized responses across booking, arrival, stay, and
  checkout.
* Staff teams often coordinate manually through calls, messaging, or memory.
* Room state can drift when housekeeping, front desk, and maintenance are not
  synchronized.
* Infrastructure may be inconsistent, so the platform must degrade gracefully
  under low-bandwidth or intermittent connectivity.
* Service quality must improve without requiring a full smart-home hardware
  stack.

The resulting product promise is precise:

* An AI concierge that can converse naturally with guests.
* An operations layer that converts intent into deterministic service actions.
* A staff coordination layer that prioritizes work and closes the feedback loop.
* A sentiment and recovery layer that detects service risk before it becomes a
  bad review.

Target Users And Outcomes
-------------------------
Primary users are resort guests. Secondary users are front desk staff,
housekeeping staff, maintenance staff, and resort management.

The intended outcomes are:

* Faster service response times.
* Higher guest satisfaction and repeat bookings.
* Better operational visibility for staff and management.
* Reduced service inconsistency across stays and properties.
* Increased revenue through better recommendations, upsell timing, and service
  recovery.

System Goals
------------
The HabitaLife Digital Concierge must:

* Understand guest intent through natural conversation.
* Preserve deterministic control over bookings, room state, payments, and
  service operations.
* Separate conversational reasoning from business authority.
* Support proactive recommendations and service nudges without becoming spammy.
* Allow guests and staff to confirm important actions before execution.
* Produce an auditable trail of every AI-assisted operational decision.
* Remain usable in low-connectivity and multilingual environments.

Non-Goals
---------
The initial architecture does not assume:

* Full room-device automation through smart hardware.
* Autonomous money movement without explicit user or staff confirmation.
* Unbounded agent autonomy over operational write paths.
* Replacing all human judgment in conflict resolution, compensation, or safety
  incidents.

Architecture Principles
-----------------------
The entire platform follows these principles:

1. ``Conversational intelligence, deterministic execution``
   Natural language understanding may be probabilistic, but all state-changing
   operations must resolve to deterministic tools, APIs, and domain rules.
2. ``Propose before mutate``
   Any AI-initiated write action must pass through a confirmation surface or an
   authenticated human operator before execution.
3. ``Behavior beats hardware``
   The system substitutes behavioral understanding and staff orchestration for
   expensive IoT automation wherever possible.
4. ``Low-latency empathy, high-integrity state``
   Fast, warm guest interaction must never compromise booking, room, payment, or
   access-control correctness.
5. ``One shared operational truth``
   Room state, reservation state, service request state, and escalation state
   must be unified across guest, staff, and management views.
6. ``Human override is a first-class feature``
   Staff and managers must be able to take over, correct, reprioritize, or lock
   flows safely.
7. ``Future-ready, not future-fiction``
   Advanced agents and integrations can be designed now, but they must sit on
   the same modular monolith and domain model defined for the MVP.

Layered Platform Architecture
-----------------------------
The system is designed as a layered platform so that each layer has clear
responsibilities and interfaces.

.. list-table:: HabitaLife platform layers
   :header-rows: 1
   :widths: 18 28 28 26

   * - Layer
     - Responsibility
     - Primary Components
     - Scope
   * - Guest channels
     - Collect guest input and present responses, proposals, and updates
     - Mobile chat UI, web chat, kiosk UI, push notifications, email, optional
       SMS
     - MVP baseline with future-ready channel expansion
   * - Staff interfaces
     - Surface tasks, queues, alerts, room state, and escalations
     - Front desk console, housekeeping dashboard, maintenance dashboard,
       manager alert view
     - MVP baseline
   * - Agent runtime
     - Interpret conversation, route tasks, reason over context, assemble tool
       plans, and produce responses
     - Interaction Agent, Planner, domain agents, memory updater, policy guard
     - MVP baseline plus future-ready specialized agents
   * - Deterministic tool layer
     - Expose all read and write operations to the agents in a controlled,
       typed, auditable way
     - READ tools, WRITE tools, INTERNAL tools, EXTERNAL connectors
     - MVP baseline
   * - Core domain services
     - Own booking, room, access, service request, notification, and auth logic
     - FastAPI modules in a modular monolith
     - MVP baseline
   * - Data and memory layer
     - Store transactional truth and derived memory signals
     - PostgreSQL, optional pgvector, audit log tables, analytics events
     - PostgreSQL is MVP baseline; vector memory is future-ready extension
   * - External integrations
     - Connect HabitaLife to payments, access control, messaging, partner
       inventory, and analytics
     - Payment gateway, push/email provider, PIN/access service, translation,
       partner connectors
     - Mixed baseline and future-ready extensions

Reference Deployment Model
--------------------------
The target system remains a modular monolith built with FastAPI and PostgreSQL.
This is the correct baseline because it keeps the operational domains tightly
coordinated while preserving clear module boundaries.

Recommended logical modules are:

* ``guest_auth`` for registration, login, JWT issuance, session handling, and
  RBAC.
* ``booking`` for availability, quote generation, reservations, cancellations,
  and access-code timing.
* ``room_management`` for room metadata, room state, housekeeping transitions,
  and maintenance locks.
* ``guest_services`` for in-stay service requests, work queues, and completion
  events.
* ``agent_runtime`` for orchestration, tool policy, proposal lifecycles,
  conversation state, and memory updates.
* ``notifications`` for app push, email, SMS, staff alerts, and escalation
  delivery.
* ``analytics_and_audit`` for event streams, decision logging, operational
  metrics, and recovery analytics.

Core Domain Model
-----------------
The transactional domain continues to center on the existing MVP entities and is
expanded carefully for agentic behavior.

.. list-table:: Core entities
   :header-rows: 1
   :widths: 22 24 54

   * - Entity
     - Scope
     - Role in the system
   * - ``User``
     - MVP baseline
     - Stores guest and staff identities, credentials, role, language
       preferences, and profile-level settings
   * - ``Room``
     - MVP baseline
     - Source of truth for physical rooms, features, status, and pricing
   * - ``Amenity`` and ``RoomAmenity``
     - MVP baseline
     - Model room features and service differentiators used in search and
       recommendation
   * - ``Reservation``
     - MVP baseline
     - Links guest to room and stay dates, access-code validity, and booking
       status
   * - ``ServiceRequest``
     - MVP baseline
     - Tracks guest requests from pending through resolution
   * - ``NotificationEvent``
     - Future-ready extension
     - Records outbound guest or staff notifications and delivery status
   * - ``ProposalAction``
     - Future-ready extension
     - Stores AI-generated write proposals awaiting confirmation or expiration
   * - ``EscalationCase``
     - Future-ready extension
     - Tracks severe guest dissatisfaction, operational incidents, or service
       recovery workflows
   * - ``GuestPreferenceSignal``
     - Future-ready extension
     - Stores derived preferences such as dining timing, quiet hours, family
       travel, accessibility needs, or favorite activities
   * - ``ConversationMemorySnapshot``
     - Future-ready extension
     - Stores condensed stay-specific and long-term memory summaries used by the
       planner and interaction agent

Canonical Core Enums
--------------------
The following states must remain explicit and shared across the system.

Room states
^^^^^^^^^^^

* ``AVAILABLE``: Ready to be booked and occupied.
* ``BOOKED``: Reserved for a future stay but not yet occupied.
* ``OCCUPIED``: Guest has checked in and access is active.
* ``NEEDS_CLEANING``: Previous stay ended; room must be serviced before reuse.
* ``MAINTENANCE_LOCK``: Room cannot be assigned because of an active issue or
  manual block.

Reservation states
^^^^^^^^^^^^^^^^^^

* ``PENDING_CONFIRMATION``: Quote exists but booking is not finalized.
* ``CONFIRMED``: Reservation created successfully.
* ``CHECKED_IN``: Guest has arrived and accessed the room.
* ``CHECKED_OUT``: Stay has ended and room turnover can begin.
* ``CANCELLED``: Reservation was canceled.
* ``NO_SHOW``: Reservation window passed without successful check-in.

Service request states
^^^^^^^^^^^^^^^^^^^^^^

* ``PENDING``
* ``ACKNOWLEDGED``
* ``IN_PROGRESS``
* ``BLOCKED``
* ``RESOLVED``
* ``CANCELLED``

Escalation severities
^^^^^^^^^^^^^^^^^^^^^

* ``LOW``: Mild dissatisfaction or recoverable delay.
* ``MEDIUM``: Clear service risk that requires staff visibility.
* ``HIGH``: High urgency issue affecting stay quality.
* ``CRITICAL``: Manager intervention required immediately.

Notification priorities
^^^^^^^^^^^^^^^^^^^^^^^

* ``LOW``
* ``NORMAL``
* ``HIGH``
* ``URGENT``

Staff assignment priorities
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``P1_IMMEDIATE``
* ``P2_TIME_SENSITIVE``
* ``P3_STANDARD``
* ``P4_DEFERRED``

Agent System Overview
---------------------
The HabitaLife Digital Concierge is not a single assistant. It is a bounded
agent system where each agent owns a narrow job and only the planner can compose
multi-step actions.

.. list-table:: Agent topology
   :header-rows: 1
   :widths: 18 30 28 24

   * - Agent
     - Core mission
     - Primary inputs
     - Allowed outputs
   * - Interaction Agent
     - Maintain tone, dialogue continuity, and guest-facing clarity
     - User message, active reservation context, memory summary, planner result
     - Response drafts, clarification prompts, sentiment cues
   * - Planner Orchestrator
     - Decide which agents and tools should be used for a request
     - Intent envelope, context snapshot, policy constraints
     - Execution plan, tool calls, handoff decision
   * - Search and Knowledge Agent
     - Resolve factual questions and policy lookup
     - Knowledge queries, property FAQs, service catalog
     - Ranked evidence, answer summaries, confidence score
   * - Booking Agent
     - Handle room discovery, quotes, booking changes, and policy-aware booking
       actions
     - Dates, guest count, room preferences, booking policies
     - Room options, quotes, booking proposals
   * - Guest Reception and Check-In Agent
     - Manage pre-arrival readiness, access-code explanation, and check-in flow
     - Reservation context, arrival time, access status
     - Check-in proposals, arrival instructions, failure escalation
   * - Service Request Agent
     - Convert stay-time needs into structured service requests
     - Guest message, stay context, service catalog
     - Ticket proposals, guest confirmations, update summaries
   * - Housekeeping Dispatch Agent
     - Prioritize cleaning and linen workflows
     - Checkout events, room state, workload, SLA rules
     - Queue ranking, dispatch suggestions, cleaning updates
   * - Maintenance Triage Agent
     - Detect issue patterns and route maintenance work
     - Issue reports, room history, severity signals
     - Maintenance tickets, room locks, escalation advice
   * - Sentiment and Recovery Agent
     - Detect dissatisfaction and coordinate recovery
     - Conversation transcript, sentiment score, unresolved delays
     - Recovery case creation, manager alerts, tone adjustments
   * - Notification Agent
     - Deliver timely guest and staff updates through approved channels
     - Delivery intent, audience, priority, channel availability
     - Notification proposals, send results, retry signals
   * - Itinerary and Recommendation Agent
     - Personalize activities, dining, and timing suggestions
     - Preferences, stay timeline, weather, occupancy patterns
     - Ranked recommendations, proactive nudges
   * - Memory Update Agent
     - Convert interactions into stable preference and behavior signals
     - Transcript chunks, booking history, service outcomes
     - Memory deltas, confidence-tagged preference updates
   * - Policy and Permission Guard
     - Enforce confirmation rules, RBAC, and safety checks on every write
     - Proposed action, actor role, risk tier, policy rules
     - Allowed, blocked, or escalated execution decision

Agent Responsibilities In Detail
--------------------------------
Each agent has a bounded scope and explicit non-responsibilities.

Interaction Agent
^^^^^^^^^^^^^^^^^
Responsibilities:

* Maintain a consistent concierge persona.
* Resolve pronouns and short references within the current session.
* Adapt tone for calm, celebratory, urgent, apologetic, or managerial moments.
* Ask clarifying questions only when uncertainty materially changes execution.

Must not:

* Directly mutate operational state.
* Invent room availability, prices, or staff actions.
* Claim a task is complete without a deterministic status update.

Planner Orchestrator
^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Decompose composite requests into executable sub-tasks.
* Decide whether a request is informational, transactional, or escalatory.
* Sequence tool calls and specialized agent handoffs.
* Ensure every write proposal includes a clear reason, impact, and confirmation
  target.

Must not:

* Skip policy validation.
* Bypass confirmation on AI-triggered write actions.
* Collapse independent tasks into one opaque write.

Search And Knowledge Agent
^^^^^^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Answer service, property, amenity, and policy questions.
* Retrieve facts from structured catalogs and knowledge sources.
* Provide evidence-backed answers with explicit uncertainty.

Must not:

* Fabricate property rules or operating hours.
* Use stale cached answers when a live tool lookup is required.

Booking Agent
^^^^^^^^^^^^^
Responsibilities:

* Search inventory, prepare quotes, and build booking-related proposals.
* Explain rate differences, room features, and cancellation logic.
* Evaluate room-fit based on guest preferences such as quietness, views,
  accessibility, or family size.

Must not:

* Create or modify reservations without confirmation.
* Promise upgrades or discounts outside policy.

Guest Reception And Check-In Agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Guide the guest from confirmed reservation to successful arrival.
* Present access instructions, arrival steps, and identity requirements.
* Detect arrival friction and escalate quickly when a guest is locked out.

Must not:

* Extend access beyond authorized windows.
* Mark a guest checked in without validated evidence.

Service Request Agent
^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Translate guest needs into clean structured tickets.
* Merge duplicates where appropriate.
* Keep the guest informed as requests move through the queue.

Must not:

* Invent completion times.
* Open ambiguous requests when critical details are missing.

Housekeeping Dispatch Agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Rank rooms by urgency, occupancy impact, and workload constraints.
* Surface late-sleeper or privacy preferences to avoid poor timing.
* Coordinate linen, turnover, and readiness updates.

Must not:

* Mark rooms available unless the completion event is validated.

Maintenance Triage Agent
^^^^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Classify issue severity.
* Detect repeated complaints for the same room or asset.
* Trigger room locks when safety or severe comfort issues are present.

Must not:

* Leave a severe issue un-escalated because the guest tone seems polite.

Sentiment And Recovery Agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Score real-time guest emotion and service risk.
* Trigger human attention before checkout dissatisfaction becomes permanent.
* Recommend apologies, compensatory gestures, or escalation pathways within
  policy.

Must not:

* Offer compensation or refunds without policy approval and confirmation.

Notification Agent
^^^^^^^^^^^^^^^^^^
Responsibilities:

* Select the best delivery channel for the event.
* Keep messages short, contextual, and traceable.
* Retry transient failures without creating notification spam.

Must not:

* Send duplicate urgent alerts without deduplication logic.

Itinerary And Recommendation Agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Suggest activities, dining, and timing windows suited to guest context.
* Blend preferences, weather, occupancy, and resort schedule.
* Generate proactive but non-intrusive recommendations.

Must not:

* Present speculative partner availability as confirmed inventory.

Memory Update Agent
^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Convert repeated signals into stable preferences.
* Track session memory separately from durable profile memory.
* Store confidence values and source evidence for behavioral inferences.

Must not:

* Promote a one-off request into a long-term preference without confidence
  thresholds.

Policy And Permission Guard
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Responsibilities:

* Enforce RBAC and confirmability on every agent-initiated write.
* Verify actor, scope, risk tier, and policy compatibility.
* Block or escalate unsafe proposals.

Must not:

* Allow special-case bypasses that are invisible to audit logs.

Runtime Contracts
-----------------
Every agent handoff and tool call must use explicit machine-readable contracts.

Canonical Intent Envelope
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "message_id": "msg_01",
     "guest_id": "guest_123",
     "reservation_id": "res_456",
     "channel": "mobile_chat",
     "language": "en",
     "raw_text": "Can I get two extra towels and a quiet dinner spot tonight?",
     "intent": {
       "primary": "service_and_recommendation",
       "secondary": ["linen_request", "dining_recommendation"]
     },
     "entities": {
       "items": ["extra towels"],
       "quantity": 2,
       "time_hint": "tonight",
       "preference_signals": ["quiet atmosphere"]
     },
     "sentiment": {
       "label": "neutral",
       "score": -0.08
     },
     "urgency": {
       "level": "P3_STANDARD",
       "reason": "no failure or deadline breach detected"
     },
     "reservation_context": {
       "stay_status": "CHECKED_IN",
       "room_id": "room_204",
       "party_type": "family"
     },
     "confidence": 0.93,
     "routed_agents": ["ServiceRequestAgent", "ItineraryRecommendationAgent"]
   }

Canonical Agent-To-Tool Contract
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "tool_name": "create_service_request",
     "tool_type": "WRITE",
     "permission": "guest_confirm_required",
     "arguments": {
       "reservation_id": "res_456",
       "request_type": "extra_towels",
       "quantity": 2
     },
     "reason": "Guest explicitly requested extra towels during active stay",
     "proposal_id": "prop_789",
     "requires_confirmation": true,
     "idempotency_key": "stay_res_456_towels_2026-04-03T12:30:00Z",
     "result": null,
     "error": null
   }

Canonical Proposal And Confirmation Envelope
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "proposal_id": "prop_789",
     "action_summary": "Request 2 extra towels for Room 204",
     "actor_role": "guest",
     "risk_level": "low_operational",
     "expires_at": "2026-04-03T12:45:00Z",
     "impacted_entities": {
       "guest_id": "guest_123",
       "reservation_id": "res_456",
       "room_id": "room_204"
     },
     "confirmation_ui": {
       "title": "Confirm towel request",
       "body": "We will notify staff and track the request in real time.",
       "confirm_label": "Confirm request",
       "cancel_label": "Cancel"
     },
     "post_confirm_execution": {
       "tool_name": "create_service_request",
       "idempotency_key": "stay_res_456_towels_2026-04-03T12:30:00Z"
     }
   }

Deterministic Tool System
-------------------------
All agent execution must flow through a deterministic tool system. The tool
system is the contract boundary between probabilistic reasoning and trusted
business operations.

Tool Types
^^^^^^^^^^

* ``READ`` tools retrieve state and execute immediately.
* ``WRITE`` tools mutate system state and require a confirmation or authenticated
  human action before execution.
* ``INTERNAL`` tools are model/runtime helpers used inside the agent layer and
  never exposed directly to end users.
* ``EXTERNAL`` connectors are adapter-backed integrations used by domain tools
  to reach external systems safely.

Permission Model
^^^^^^^^^^^^^^^^

.. code-block:: text

   Guest Message / Staff Event
            |
            v
   Interaction Agent -> Planner Orchestrator
            |
            v
      Tool selection stage
            |
     +------+------+
     |             |
     v             v
   READ         WRITE
     |             |
   Execute      Build proposal
     |             |
   Return       Policy guard check
   result           |
                     v
                Confirm / reject
                     |
                     v
                 Execute write
                     |
                     v
                 Notify + audit

Standard Tool Entry Schema
^^^^^^^^^^^^^^^^^^^^^^^^^^
Every tool entry in the catalog below documents the same fields:

* ``Purpose``: Why the tool exists.
* ``Caller agents``: Which agents are allowed to invoke it.
* ``Required context``: Minimum identifiers and state needed.
* ``Key parameters``: Arguments that materially shape execution.
* ``Response shape``: The deterministic structure returned.
* ``Permission``: READ, WRITE, INTERNAL, or EXTERNAL plus confirmation rule.
* ``Confirmation``: Who must approve, if anyone.
* ``Idempotency``: Whether duplicate calls are safe and how they are handled.
* ``Fallback``: What the system should do if the tool is unavailable or
  ambiguous.
* ``Audit``: What must be logged in sanitized form.

READ Tool Catalog
-----------------
READ tools execute automatically and never mutate system state.

Guest Profile And Memory Reads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``get_guest_profile_summary`` [Future-ready extension]
  Purpose:
    Returns a compact guest profile summary for personalization, including
    preferred language, stay history count, accessibility flags, and notable
    service preferences.
  Caller agents:
    Interaction Agent, Planner Orchestrator, Itinerary and Recommendation
    Agent, Guest Reception and Check-In Agent.
  Required context:
    ``guest_id``.
  Key parameters:
    ``include_preference_signals``, ``include_recent_stays``.
  Response shape:
    Guest summary object with profile traits, stable preferences, and confidence
    scores.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Return a minimal profile with no inferred preferences if no durable memory
    exists.
  Audit:
    Log tool name, guest scope, and response latency.

``get_current_stay_context`` [MVP baseline]
  Purpose:
    Returns the active reservation, room, arrival/departure timeline, and open
    service requests for the current stay.
  Caller agents:
    Interaction Agent, Planner Orchestrator, Service Request Agent, Sentiment
    and Recovery Agent.
  Required context:
    ``guest_id`` or ``reservation_id``.
  Key parameters:
    ``include_open_requests``, ``include_room_status``.
  Response shape:
    Reservation context object with stay status, room number, open tasks, and
    service history for the active stay.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    If no active stay exists, return ``stay_status = none`` and allow the
    interaction agent to pivot to booking or general information mode.
  Audit:
    Log actor role and reservation scope.

``get_guest_preference_signals`` [Future-ready extension]
  Purpose:
    Returns derived guest signals such as late-sleeper behavior, family travel,
    quiet-room preference, dining timing, celebration signals, or allergy
    notes.
  Caller agents:
    Planner Orchestrator, Housekeeping Dispatch Agent, Itinerary and
    Recommendation Agent.
  Required context:
    ``guest_id``.
  Key parameters:
    ``confidence_threshold``.
  Response shape:
    Preference signal list with source evidence and confidence.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Use session-only memory if durable profile memory is unavailable.
  Audit:
    Log count of signals returned, not raw transcript content.

``get_guest_service_history`` [Future-ready extension]
  Purpose:
    Returns recent completed and unresolved service requests to improve
    recommendations and recovery behavior.
  Caller agents:
    Sentiment and Recovery Agent, Service Request Agent, Planner Orchestrator.
  Required context:
    ``guest_id`` or ``reservation_id``.
  Key parameters:
    ``limit``, ``only_unresolved``.
  Response shape:
    Array of service request summaries with timestamps and outcomes.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Return empty history and continue with current-stay context.
  Audit:
    Log request scope and result count.

Booking And Availability Reads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``search_room_inventory`` [MVP baseline]
  Purpose:
    Returns rooms available for a date range and occupancy requirement.
  Caller agents:
    Booking Agent, Planner Orchestrator.
  Required context:
    Check-in date, check-out date, guest count.
  Key parameters:
    ``room_type``, ``max_price``, ``view_preference``, ``accessibility_needed``.
  Response shape:
    Room option list with availability flag and room metadata.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Return closest alternatives and unavailable reasons.
  Audit:
    Log search window and candidate count.

``get_rate_quote`` [MVP baseline]
  Purpose:
    Calculates total booking price and pricing breakdown for a selected room and
    stay.
  Caller agents:
    Booking Agent.
  Required context:
    ``room_id``, dates, guest count.
  Key parameters:
    ``include_tax_breakdown``, ``promo_code``.
  Response shape:
    Quoted price object with nightly breakdown, fees, and expiration time.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only for the same inputs.
  Fallback:
    If pricing rules are unavailable, stop the transaction and escalate to front
    desk assistance.
  Audit:
    Log quote identifier and expiry.

``get_reservation_record`` [MVP baseline]
  Purpose:
    Returns full reservation details including status, room, dates, and access
    eligibility.
  Caller agents:
    Booking Agent, Guest Reception and Check-In Agent, Interaction Agent.
  Required context:
    ``reservation_id``.
  Key parameters:
    ``include_access_window``.
  Response shape:
    Reservation object.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Return ``not_found`` with a user-safe explanation path.
  Audit:
    Log reservation lookup outcome.

``get_access_code_status`` [MVP baseline]
  Purpose:
    Returns whether a reservation has a valid access code, its activation window,
    and any failure reason.
  Caller agents:
    Guest Reception and Check-In Agent, Interaction Agent.
  Required context:
    ``reservation_id``.
  Key parameters:
    None.
  Response shape:
    Access status object with active, inactive, expired, or blocked status.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Route to manual check-in support if access state is uncertain.
  Audit:
    Log lookup and result state.

Room State Reads
^^^^^^^^^^^^^^^^

``get_room_status_snapshot`` [MVP baseline]
  Purpose:
    Returns the current room state, occupancy status, and outstanding locks.
  Caller agents:
    Housekeeping Dispatch Agent, Maintenance Triage Agent, Guest Reception and
    Check-In Agent.
  Required context:
    ``room_id``.
  Key parameters:
    ``include_last_transition``.
  Response shape:
    Room state object with timestamps and actor metadata.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Mark room status as uncertain and require human review before making promises
    to the guest.
  Audit:
    Log room scope and state returned.

``get_room_feature_matrix`` [MVP baseline]
  Purpose:
    Returns structured room features and amenities used for matching and
    explanation.
  Caller agents:
    Booking Agent, Itinerary and Recommendation Agent.
  Required context:
    ``room_id`` or room candidate list.
  Key parameters:
    ``include_images``, ``include_amenity_categories``.
  Response shape:
    Feature object with view, size, amenities, and max occupancy.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Use base room metadata only.
  Audit:
    Log room count queried.

``get_room_issue_history`` [Future-ready extension]
  Purpose:
    Returns recurring issue signals for a room to support proactive maintenance
    and recovery.
  Caller agents:
    Maintenance Triage Agent, Sentiment and Recovery Agent.
  Required context:
    ``room_id``.
  Key parameters:
    ``days_back``, ``include_resolution_notes``.
  Response shape:
    Issue summary list grouped by problem type and frequency.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Continue without recurrence detection.
  Audit:
    Log room scope and issue cluster count.

``get_housekeeping_queue`` [Future-ready extension]
  Purpose:
    Returns current cleaning backlog with readiness SLA, staff assignment, and
    priority score.
  Caller agents:
    Housekeeping Dispatch Agent, Planner Orchestrator.
  Required context:
    Property or floor scope.
  Key parameters:
    ``include_staff_load``, ``include_checkout_events``.
  Response shape:
    Ordered queue of rooms with urgency reasons.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Fall back to chronological queueing if live scoring data is unavailable.
  Audit:
    Log queue version and result size.

Staff And Workload Reads
^^^^^^^^^^^^^^^^^^^^^^^^

``get_active_staff_roster`` [Future-ready extension]
  Purpose:
    Returns currently active staff members by team, shift, and location.
  Caller agents:
    Housekeeping Dispatch Agent, Maintenance Triage Agent, Notification Agent.
  Required context:
    Team or property scope.
  Key parameters:
    ``team_type``, ``include_contact_channel``.
  Response shape:
    Staff roster array with availability and role.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Use most recent shift schedule snapshot.
  Audit:
    Log team scope and active count.

``get_staff_load_scores`` [Future-ready extension]
  Purpose:
    Returns workload scores used to avoid overloading a single staff member.
  Caller agents:
    Housekeeping Dispatch Agent, Maintenance Triage Agent.
  Required context:
    Team scope.
  Key parameters:
    ``include_travel_time_estimate``.
  Response shape:
    Staff load list with current task count, SLA pressure, and assignment score.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Degrade to equal distribution.
  Audit:
    Log team scope and scoring timestamp.

``get_shift_coverage_window`` [Future-ready extension]
  Purpose:
    Returns staffing coverage for the next few hours so the planner can set
    realistic expectations.
  Caller agents:
    Planner Orchestrator, Notification Agent, Sentiment and Recovery Agent.
  Required context:
    Team or property scope.
  Key parameters:
    ``hours_ahead``.
  Response shape:
    Coverage summary with expected gaps.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Use static shift template with low-confidence flag.
  Audit:
    Log horizon requested and confidence level.

Knowledge, Policy, And Recommendation Reads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``search_property_knowledge_base`` [MVP baseline]
  Purpose:
    Answers factual guest questions about the property, services, dining hours,
    policies, and local guidance.
  Caller agents:
    Search and Knowledge Agent, Interaction Agent.
  Required context:
    Query string and property scope.
  Key parameters:
    ``topic``, ``top_k``.
  Response shape:
    Ranked snippets or structured knowledge records with confidence.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    State uncertainty and hand off to staff for unanswered questions.
  Audit:
    Log topic and retrieval latency.

``get_service_catalog`` [MVP baseline]
  Purpose:
    Returns structured list of available guest services and their requestable
    parameters.
  Caller agents:
    Service Request Agent, Planner Orchestrator.
  Required context:
    Property scope.
  Key parameters:
    ``include_schedule_constraints``.
  Response shape:
    Service catalog with request types, availability windows, and required
    fields.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Use cached service catalog with a staleness warning.
  Audit:
    Log catalog version.

``get_policy_rules`` [Future-ready extension]
  Purpose:
    Returns structured policies for cancellations, late checkout, refunds,
    compensation, room changes, and special approvals.
  Caller agents:
    Booking Agent, Sentiment and Recovery Agent, Policy and Permission Guard.
  Required context:
    Policy domain and reservation context.
  Key parameters:
    ``policy_domain``, ``reservation_status``.
  Response shape:
    Policy rule set with eligibility and approval level.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Block risky action and require staff review.
  Audit:
    Log policy domain and rule version.

``get_recommendation_candidates`` [Future-ready extension]
  Purpose:
    Returns recommendation candidates for dining, spa, activities, transport,
    and experience bundles.
  Caller agents:
    Itinerary and Recommendation Agent.
  Required context:
    Guest profile, stay timeline, and property scope.
  Key parameters:
    ``category``, ``time_window``, ``include_capacity_estimate``.
  Response shape:
    Candidate list with metadata and ranking features.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Use static featured recommendations.
  Audit:
    Log category and candidate count.

``get_local_activity_catalog`` [Future-ready extension]
  Purpose:
    Returns optional local experiences, partner offers, transport windows, and
    off-property activities.
  Caller agents:
    Itinerary and Recommendation Agent, Search and Knowledge Agent.
  Required context:
    Property location and stay timeline.
  Key parameters:
    ``category``, ``guest_type``, ``weather_sensitive_only``.
  Response shape:
    Activity list with booking type, partner source, and operational notes.
  Permission:
    READ, auto-execute.
  Confirmation:
    None.
  Idempotency:
    Read-only.
  Fallback:
    Return in-property options only.
  Audit:
    Log category and provider source.

WRITE Tool Catalog
------------------
WRITE tools mutate state. They are never auto-executed by the agent runtime.
They must pass through the Policy and Permission Guard and then through a guest,
staff, or admin confirmation surface.

Service Request Writes
^^^^^^^^^^^^^^^^^^^^^^

``create_service_request`` [MVP baseline]
  Purpose:
    Creates a new in-stay guest request such as extra towels, room service,
    late checkout review, or amenity delivery.
  Caller agents:
    Service Request Agent, Planner Orchestrator.
  Required context:
    Active ``reservation_id`` and validated request type.
  Key parameters:
    ``request_type``, ``quantity``, ``notes``, ``requested_for_time``.
  Response shape:
    New service request identifier and initial status.
  Permission:
    WRITE, guest or staff confirmation required.
  Confirmation:
    Guest confirms in guest UI; staff can confirm directly in dashboard when the
    request originates from staff.
  Idempotency:
    Duplicate requests with the same idempotency key return the original request.
  Fallback:
    If catalog validation fails, ask for clarification instead of writing.
  Audit:
    Log request type, actor role, and confirmation result.

``update_service_request_status`` [MVP baseline]
  Purpose:
    Transitions a service request through acknowledgment, in progress, blocked,
    or resolved states.
  Caller agents:
    Service Request Agent, Housekeeping Dispatch Agent, Maintenance Triage
    Agent.
  Required context:
    ``service_request_id`` and actor role.
  Key parameters:
    ``new_status``, ``resolution_note``.
  Response shape:
    Updated request record.
  Permission:
    WRITE, staff confirmation required.
  Confirmation:
    Staff dashboard confirmation or authenticated staff action.
  Idempotency:
    Repeating the same terminal status returns the current record.
  Fallback:
    If status conflict exists, refresh current state and re-evaluate.
  Audit:
    Log previous state, new state, and acting user.

``reprioritize_service_request`` [Future-ready extension]
  Purpose:
    Raises or lowers queue priority when sentiment, VIP status, medical need, or
    SLA pressure changes.
  Caller agents:
    Sentiment and Recovery Agent, Housekeeping Dispatch Agent, Planner
    Orchestrator.
  Required context:
    ``service_request_id`` and reason code.
  Key parameters:
    ``priority``, ``reason_code``.
  Response shape:
    Updated priority metadata.
  Permission:
    WRITE, staff or manager confirmation required.
  Confirmation:
    Manager confirmation for critical overrides; standard staff confirmation for
    non-critical queue changes.
  Idempotency:
    Same priority and reason key do not create duplicate reprioritization events.
  Fallback:
    Keep current priority and alert dashboard.
  Audit:
    Log priority delta and reason class.

Booking And Reservation Writes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``create_reservation`` [MVP baseline]
  Purpose:
    Creates a new reservation after quote acceptance.
  Caller agents:
    Booking Agent.
  Required context:
    Selected room, stay dates, guest identity, and pricing token.
  Key parameters:
    ``room_id``, ``check_in_date``, ``check_out_date``, ``guest_count``,
    ``pricing_token``.
  Response shape:
    Reservation identifier, status, and access generation eligibility.
  Permission:
    WRITE, guest confirmation required.
  Confirmation:
    Guest confirms booking in UI; payment confirmation may be required before
    execution.
  Idempotency:
    Same quote token and idempotency key return the existing reservation.
  Fallback:
    Refresh inventory and quote if room availability changed.
  Audit:
    Log booking scope, quote token, and confirmation source.

``modify_reservation`` [Future-ready extension]
  Purpose:
    Changes dates, room assignment, or guest count within policy.
  Caller agents:
    Booking Agent, Guest Reception and Check-In Agent.
  Required context:
    Existing ``reservation_id`` and policy eligibility.
  Key parameters:
    ``new_check_in_date``, ``new_check_out_date``, ``new_room_id``,
    ``guest_count``.
  Response shape:
    Updated reservation plus any new pricing delta.
  Permission:
    WRITE, guest confirmation required; admin confirmation for restricted
    exceptions.
  Confirmation:
    Guest confirms the change; staff/admin may confirm exception cases.
  Idempotency:
    Same target change key returns the existing modified reservation.
  Fallback:
    Offer alternative rooms or dates instead of partial silent failure.
  Audit:
    Log original state, target state, and approval path.

``cancel_reservation`` [MVP baseline]
  Purpose:
    Cancels a reservation within policy.
  Caller agents:
    Booking Agent.
  Required context:
    ``reservation_id`` and cancellation policy.
  Key parameters:
    ``reason``, ``requested_by``.
  Response shape:
    Cancel result with refund eligibility summary.
  Permission:
    WRITE, guest or staff confirmation required.
  Confirmation:
    Guest or authorized staff confirms cancellation.
  Idempotency:
    Repeated cancellation on an already canceled reservation returns current
    state.
  Fallback:
    If cancellation is not allowed automatically, route to staff approval.
  Audit:
    Log policy outcome and actor.

Check-In And Access Writes
^^^^^^^^^^^^^^^^^^^^^^^^^^

``issue_access_code`` [MVP baseline]
  Purpose:
    Generates or synchronizes a time-bound access code for a confirmed
    reservation.
  Caller agents:
    Guest Reception and Check-In Agent.
  Required context:
    Confirmed reservation and eligible access window.
  Key parameters:
    ``reservation_id``, ``activation_time``, ``expiry_time``.
  Response shape:
    Access code metadata and delivery state.
  Permission:
    WRITE, staff confirmation or eligible automated post-booking confirmation.
  Confirmation:
    Staff can confirm manually; system can auto-stage after successful booking if
    policy allows.
  Idempotency:
    Existing active code is returned unless rotation is explicitly requested.
  Fallback:
    Route to manual front desk issuance if connector is unavailable.
  Audit:
    Log reservation scope and code issuance result, never raw code value.

``validate_guest_check_in`` [MVP baseline]
  Purpose:
    Marks a reservation as checked in after successful arrival validation.
  Caller agents:
    Guest Reception and Check-In Agent.
  Required context:
    Reservation, valid access event or front desk verification.
  Key parameters:
    ``reservation_id``, ``verification_source``.
  Response shape:
    Updated reservation and room occupancy status.
  Permission:
    WRITE, staff confirmation or validated access event required.
  Confirmation:
    Staff confirms if the trigger is manual; access subsystem can serve as the
    confirmation source when trusted.
  Idempotency:
    Repeated check-in returns current checked-in state.
  Fallback:
    Escalate to front desk if validation is ambiguous.
  Audit:
    Log verification source and timestamp.

``register_guest_checkout`` [Future-ready extension]
  Purpose:
    Marks stay completion and triggers downstream turnover workflows.
  Caller agents:
    Guest Reception and Check-In Agent, Housekeeping Dispatch Agent.
  Required context:
    Active reservation in checked-in state.
  Key parameters:
    ``reservation_id``, ``checkout_source``.
  Response shape:
    Updated reservation, room state transition signal, and housekeeping trigger.
  Permission:
    WRITE, guest or staff confirmation required.
  Confirmation:
    Guest confirms digital checkout or staff confirms on behalf of guest.
  Idempotency:
    Repeated checkout returns already checked-out state.
  Fallback:
    If final charges are unresolved, keep checkout pending and notify staff.
  Audit:
    Log source and downstream actions emitted.

Room State Override Writes
^^^^^^^^^^^^^^^^^^^^^^^^^^

``mark_room_needs_cleaning`` [MVP baseline]
  Purpose:
    Moves a room into cleaning-required state after checkout or verified vacancy.
  Caller agents:
    Housekeeping Dispatch Agent.
  Required context:
    ``room_id`` and a valid triggering event.
  Key parameters:
    ``reason``.
  Response shape:
    Updated room state.
  Permission:
    WRITE, staff confirmation required.
  Confirmation:
    Staff or validated checkout event.
  Idempotency:
    Repeated transition to the same state is a no-op.
  Fallback:
    Keep prior state and raise mismatch alert if preconditions fail.
  Audit:
    Log previous room state and trigger source.

``mark_room_cleaned`` [MVP baseline]
  Purpose:
    Marks room turnover complete and makes the room available when no conflicting
    lock exists.
  Caller agents:
    Housekeeping Dispatch Agent.
  Required context:
    ``room_id`` currently in ``NEEDS_CLEANING``.
  Key parameters:
    ``housekeeper_id``, ``inspection_passed``.
  Response shape:
    Updated room state and readiness timestamp.
  Permission:
    WRITE, housekeeping confirmation required.
  Confirmation:
    Authenticated staff action or supervisor confirmation.
  Idempotency:
    Repeated completion event returns current available state if no intervening
    lock exists.
  Fallback:
    If a maintenance lock exists, keep room unavailable and notify staff.
  Audit:
    Log staff actor and inspection result.

``lock_room_for_maintenance`` [Future-ready extension]
  Purpose:
    Prevents room assignment when a maintenance issue affects habitability or
    guest safety.
  Caller agents:
    Maintenance Triage Agent, Sentiment and Recovery Agent.
  Required context:
    ``room_id`` and issue severity.
  Key parameters:
    ``issue_type``, ``severity``, ``reason``.
  Response shape:
    Room lock record and room state.
  Permission:
    WRITE, staff or manager confirmation required.
  Confirmation:
    Maintenance lead or manager confirms.
  Idempotency:
    Same active issue does not create duplicate locks.
  Fallback:
    If lock cannot be applied, immediately alert management because room safety
    may be at risk.
  Audit:
    Log issue class, severity, and approver.

``release_room_from_maintenance`` [Future-ready extension]
  Purpose:
    Removes maintenance lock once issue resolution is verified.
  Caller agents:
    Maintenance Triage Agent.
  Required context:
    Active lock and repair confirmation.
  Key parameters:
    ``room_id``, ``resolution_note``.
  Response shape:
    Updated room state and lock status.
  Permission:
    WRITE, staff confirmation required.
  Confirmation:
    Authorized maintenance or operations supervisor confirms.
  Idempotency:
    Releasing an already released lock is a no-op.
  Fallback:
    Keep lock in place if repair verification is incomplete.
  Audit:
    Log lock duration and resolution actor.

Escalation, Notification, And Payment Writes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``create_manager_escalation`` [Future-ready extension]
  Purpose:
    Opens a recovery case for severe dissatisfaction or operational incidents.
  Caller agents:
    Sentiment and Recovery Agent, Planner Orchestrator.
  Required context:
    Guest context, issue summary, severity score.
  Key parameters:
    ``severity``, ``summary``, ``impacted_request_ids``.
  Response shape:
    Escalation case record and delivery targets.
  Permission:
    WRITE, system proposal plus manager acknowledgment required.
  Confirmation:
    Manager acknowledgment in dashboard; critical alerts may auto-send before
    acknowledgment while the case itself awaits confirmation.
  Idempotency:
    Same root incident key returns the existing open case.
  Fallback:
    Send direct urgent notification if case creation subsystem is degraded.
  Audit:
    Log severity, guest scope, and acknowledgment time.

``send_operational_notification`` [Future-ready extension]
  Purpose:
    Sends a staff or guest notification after approval by the notification
    policy layer.
  Caller agents:
    Notification Agent, Planner Orchestrator.
  Required context:
    Audience, channel, and template or message body.
  Key parameters:
    ``audience_type``, ``channel``, ``priority``, ``message``.
  Response shape:
    Notification event record with delivery status.
  Permission:
    WRITE, system proposal with policy approval; urgent manager alerts may be
    policy-authorized for immediate send.
  Confirmation:
    Depends on audience and risk. Routine transactional notices can be system
    confirmed; sensitive guest communications may require staff review.
  Idempotency:
    Notification dedupe key prevents repeated sends for the same event.
  Fallback:
    Queue for retry or downgrade to alternate channel.
  Audit:
    Log audience, template, priority, and delivery result.

``create_payment_intent`` [Future-ready extension]
  Purpose:
    Creates a payment or deposit authorization request for booking or
    stay-related charges.
  Caller agents:
    Booking Agent, Guest Reception and Check-In Agent.
  Required context:
    Guest identity, amount, currency, and charge reason.
  Key parameters:
    ``amount``, ``currency``, ``reason_code``.
  Response shape:
    Payment intent metadata and next action.
  Permission:
    WRITE, guest confirmation required.
  Confirmation:
    Guest confirms payment initiation.
  Idempotency:
    Same booking and charge reason return the existing pending payment intent.
  Fallback:
    Pause booking confirmation until payment provider recovers or staff takes
    over.
  Audit:
    Log amount, currency, and reason code, never full payment instrument details.

``capture_deposit`` [Future-ready extension]
  Purpose:
    Finalizes a previously authorized deposit or stay charge.
  Caller agents:
    Booking Agent, Guest Reception and Check-In Agent.
  Required context:
    Existing payment intent and capture eligibility.
  Key parameters:
    ``payment_intent_id``, ``amount``.
  Response shape:
    Capture result and receipt reference.
  Permission:
    WRITE, guest or staff confirmation per policy.
  Confirmation:
    Explicit charge confirmation unless pre-authorized in booking terms.
  Idempotency:
    Repeated capture with same key returns prior result.
  Fallback:
    Keep booking in pending state and alert staff.
  Audit:
    Log capture result and receipt reference.

``initiate_refund`` [Future-ready extension]
  Purpose:
    Starts a refund flow for cancellations, recovery compensation, or billing
    correction.
  Caller agents:
    Sentiment and Recovery Agent, Booking Agent.
  Required context:
    Charge reference, refund amount, and policy approval.
  Key parameters:
    ``payment_reference``, ``amount``, ``refund_reason``.
  Response shape:
    Refund initiation record with expected settlement state.
  Permission:
    WRITE, manager or finance confirmation required.
  Confirmation:
    Authorized staff must confirm.
  Idempotency:
    Same charge and refund key return the existing refund request.
  Fallback:
    Record a pending manual finance task.
  Audit:
    Log refund reason and approver.

INTERNAL Tool Catalog
---------------------
INTERNAL tools are not business APIs. They are trusted runtime helpers used to
prepare or validate agent actions.

``extract_intent_envelope``
  Purpose:
    Converts raw text into the canonical intent envelope.
  Caller agents:
    Interaction Agent, Planner Orchestrator.
  Required context:
    Raw message and optional conversation history.
  Key parameters:
    ``language``, ``channel``.
  Response shape:
    Canonical intent envelope.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Deterministic for a fixed input version where possible.
  Fallback:
    Return low-confidence intent and request clarification.
  Audit:
    Log confidence and routing target, not raw private text.

``extract_entities``
  Purpose:
    Pulls structured entities such as dates, room types, quantity, timing, and
    party size from a message.
  Caller agents:
    Planner Orchestrator, Booking Agent, Service Request Agent.
  Required context:
    Message text.
  Key parameters:
    Entity domains to extract.
  Response shape:
    Entity object with confidence values.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Best-effort deterministic.
  Fallback:
    Ask targeted clarification.
  Audit:
    Log extracted entity types.

``score_sentiment``
  Purpose:
    Scores guest sentiment and likely service risk.
  Caller agents:
    Interaction Agent, Sentiment and Recovery Agent.
  Required context:
    Message text and optionally recent transcript.
  Key parameters:
    ``include_recovery_risk``.
  Response shape:
    Sentiment label, numeric score, and risk hints.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Reproducible for model version and fixed text.
  Fallback:
    Default to neutral and avoid unnecessary escalation.
  Audit:
    Log score bucket and model version.

``score_urgency``
  Purpose:
    Classifies operational urgency using timing, issue class, and sentiment.
  Caller agents:
    Planner Orchestrator, Housekeeping Dispatch Agent, Maintenance Triage Agent.
  Required context:
    Intent envelope and stay context.
  Key parameters:
    ``sla_ruleset``.
  Response shape:
    Priority score and rationale.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Deterministic for the same ruleset.
  Fallback:
    Use conservative standard priority.
  Audit:
    Log priority and rationale code.

``summarize_memory_delta``
  Purpose:
    Converts new interaction evidence into candidate long-term preferences.
  Caller agents:
    Memory Update Agent.
  Required context:
    Transcript chunks and current profile summary.
  Key parameters:
    ``min_confidence_for_promotion``.
  Response shape:
    Memory delta candidates with confidence and evidence span references.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Stable for the same inputs and model version.
  Fallback:
    Store as session-only memory.
  Audit:
    Log promoted signal types only.

``rank_recommendation_candidates``
  Purpose:
    Scores recommendation options using guest fit, timing, weather, and
    operational capacity.
  Caller agents:
    Itinerary and Recommendation Agent.
  Required context:
    Candidate list plus profile and stay context.
  Key parameters:
    ``ranking_objective``.
  Response shape:
    Ordered list with score explanations.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Deterministic for the same feature inputs and ranker version.
  Fallback:
    Use default popularity ordering.
  Audit:
    Log objective and candidate count.

``detect_policy_conflicts``
  Purpose:
    Checks whether a proposed write conflicts with policy, role, or state.
  Caller agents:
    Planner Orchestrator, Policy and Permission Guard.
  Required context:
    Proposed action and current domain state.
  Key parameters:
    ``policy_domain``.
  Response shape:
    Allow, block, or escalate result with conflict reasons.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Deterministic for current state and policy version.
  Fallback:
    Block and escalate to human review.
  Audit:
    Log decision and conflict class.

``build_confirmation_proposal``
  Purpose:
    Creates the UI-safe proposal payload for any write action.
  Caller agents:
    Planner Orchestrator, Service Request Agent, Booking Agent.
  Required context:
    Proposed tool call and user-visible summary.
  Key parameters:
    ``risk_level``, ``expires_at``.
  Response shape:
    Canonical proposal object.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Same action and idempotency key return the same proposal shape.
  Fallback:
    Do not proceed to execution if proposal generation fails.
  Audit:
    Log proposal identifier and risk level.

``score_staff_assignment``
  Purpose:
    Calculates the best available staff or team target for a new task.
  Caller agents:
    Housekeeping Dispatch Agent, Maintenance Triage Agent.
  Required context:
    Task type, location, urgency, and staff load.
  Key parameters:
    ``optimize_for``.
  Response shape:
    Ranked staff targets with assignment score.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Deterministic for the same live workload snapshot.
  Fallback:
    Assign to team queue rather than an individual.
  Audit:
    Log optimization objective and winning score band.

``decide_handover_trigger``
  Purpose:
    Determines whether the conversation should be handed to a human.
  Caller agents:
    Interaction Agent, Sentiment and Recovery Agent, Policy and Permission
    Guard.
  Required context:
    Intent, policy outcome, confidence score, and sentiment risk.
  Key parameters:
    ``handover_threshold``.
  Response shape:
    ``continue_ai``, ``needs_staff``, or ``needs_manager``.
  Permission:
    INTERNAL.
  Confirmation:
    None.
  Idempotency:
    Deterministic for the same thresholds.
  Fallback:
    Prefer human handover when uncertainty is high.
  Audit:
    Log decision and top trigger reason.

EXTERNAL Connector Catalog
--------------------------
EXTERNAL connectors are adapter-backed integrations that sit behind domain
tools. Agents should not call vendors directly; they call domain tools, and the
domain layer uses these connectors.

``payment_gateway_connector`` [Future-ready extension]
  Purpose:
    Create, authorize, capture, and refund charges through an approved payment
    provider.
  Used by:
    ``create_payment_intent``, ``capture_deposit``, ``initiate_refund``.
  Key behaviors:
    Tokenized payment handling, idempotent charge operations, status polling, and
    webhook reconciliation.
  Fallback:
    Staff-assisted payment path.

``messaging_connector`` [Future-ready extension]
  Purpose:
    Deliver email and SMS notifications to guests and staff.
  Used by:
    ``send_operational_notification`` and booking/check-in notification flows.
  Key behaviors:
    Template rendering, delivery status tracking, retry with backoff, and
    channel downgrade.
  Fallback:
    In-app notification only.

``push_notification_connector`` [Future-ready extension]
  Purpose:
    Send mobile push notifications for time-sensitive guest updates.
  Used by:
    ``send_operational_notification`` and proactive recommendation flows.
  Key behaviors:
    Device targeting, silent notifications, dedupe, and priority routing.
  Fallback:
    Email or SMS.

``digital_access_connector`` [MVP baseline]
  Purpose:
    Generate or validate access PINs or door-entry credentials.
  Used by:
    ``issue_access_code`` and ``validate_guest_check_in``.
  Key behaviors:
    Time-bound code generation, sync confirmation, activation windows, and audit
    signaling.
  Fallback:
    Manual front desk access issuance.

``pms_channel_manager_connector`` [Future-ready extension]
  Purpose:
    Synchronize reservations, room inventory, and stay events with external
    property systems if the resort already has them.
  Used by:
    Booking and reservation sync flows.
  Key behaviors:
    Two-way sync, conflict handling, source-of-truth priority, and replayable
    webhooks.
  Fallback:
    HabitaLife remains the primary record for direct bookings.

``partner_experience_connector`` [Future-ready extension]
  Purpose:
    Query and optionally reserve transport, tours, or local experiences with
    partner providers.
  Used by:
    Recommendation and itinerary flows.
  Key behaviors:
    Availability lookup, booking intent creation, partner acknowledgment, and
    failure recovery.
  Fallback:
    Present concierge-assisted booking instead of instant confirmation.

``translation_connector`` [Future-ready extension]
  Purpose:
    Provide multilingual translation for guest communication, especially
    English, Amharic, and future property languages.
  Used by:
    Interaction Agent and Notification Agent.
  Key behaviors:
    Bidirectional translation, style preservation, and confidence-tagged output.
  Fallback:
    Route to staff with language support if confidence is low.

``analytics_sink_connector`` [Future-ready extension]
  Purpose:
    Stream operational and guest-experience events to analytics or BI systems.
  Used by:
    Analytics and audit module.
  Key behaviors:
    Event batching, schema validation, and privacy-safe export.
  Fallback:
    Store locally for delayed sync.

``vector_retrieval_connector`` [Future-ready extension]
  Purpose:
    Support semantic retrieval over property knowledge and memory summaries.
  Used by:
    Search and Knowledge Agent, Memory Update Agent, Planner Orchestrator.
  Key behaviors:
    Embedding lookup, top-k retrieval, and versioned index refresh.
  Fallback:
    Use structured knowledge tables and keyword search only.

End-To-End Operational Flows
----------------------------
This section defines the most important system behaviors from guest input to
deterministic outcome.

Discovery And Booking Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Guest asks for room options, price, or booking help through chat or web UI.
2. Interaction Agent produces the intent envelope using
   ``extract_intent_envelope`` and ``extract_entities``.
3. Planner Orchestrator routes the request to Booking Agent.
4. Booking Agent calls ``search_room_inventory``, ``get_room_feature_matrix``,
   and ``get_rate_quote`` as needed.
5. Interaction Agent presents room options in guest-friendly language.
6. If the guest selects a room, Booking Agent prepares ``create_reservation``.
7. Policy and Permission Guard checks booking eligibility and pricing token.
8. Guest confirms the booking proposal.
9. The booking domain executes the reservation write and returns reservation
   details.
10. Notification Agent sends confirmation details and optional payment or
    access-code follow-up.

Failure handling:

* If inventory changed, refresh quote and explain the change.
* If the guest request is underspecified, ask only for the missing dates,
  occupancy, or room-fit criteria.
* If payment cannot be completed, keep reservation in a pending state or route
  to staff.

Pre-Arrival Personalization Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. A confirmed reservation enters the arrival window.
2. Guest Reception and Check-In Agent loads ``get_reservation_record``,
   ``get_guest_profile_summary``, and ``get_guest_preference_signals``.
3. Itinerary and Recommendation Agent evaluates arrival time, guest type, and
   available services.
4. Notification Agent prepares a pre-arrival message with check-in guidance,
   transport tips, or relevant upsells such as dinner or spa options.
5. Any recommendation that only informs can be sent directly through approved
   notification policy.
6. Any recommendation that creates a booking, payment, or guaranteed service
   must become a proposal first.

Failure handling:

* If no profile exists, use reservation data only.
* If arrival timing is unclear, keep messaging informative rather than
  assumptive.

Check-In And Access Issuance Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Guest asks about arrival or attempts digital check-in.
2. Guest Reception and Check-In Agent fetches reservation and access status via
   ``get_reservation_record`` and ``get_access_code_status``.
3. If no valid code exists and policy allows, the agent prepares
   ``issue_access_code``.
4. Staff or guest confirmation occurs based on policy and check-in stage.
5. The domain layer uses ``digital_access_connector`` to generate or sync the
   access credential.
6. Notification Agent delivers the credential guidance through approved
   channels.
7. When access validation succeeds or front desk confirms arrival, the system
   executes ``validate_guest_check_in``.
8. Reservation becomes ``CHECKED_IN`` and room state becomes ``OCCUPIED``.

Failure handling:

* If access issuance fails, front desk handover is immediate.
* If reservation dates do not match arrival, the system blocks autonomous
  check-in and routes to staff.

In-Stay Service Request Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Guest sends a request such as extra towels, breakfast in room, or late
   cleaning.
2. Interaction Agent and Planner Orchestrator resolve intent and stay context.
3. Service Request Agent validates the request against ``get_service_catalog``.
4. The agent builds a ``create_service_request`` proposal with an
   idempotency key.
5. Guest confirms the request.
6. Guest services module creates the ticket in ``PENDING`` state.
7. Notification Agent or staff dashboard surfaces the request to the correct
   team.
8. Staff acknowledges work and the status changes to ``ACKNOWLEDGED`` or
   ``IN_PROGRESS``.
9. When work is completed, staff marks the request ``RESOLVED``.
10. Guest receives a completion update and the Memory Update Agent captures any
    preference signal.

Failure handling:

* If request type is unsupported, the system explains the limitation and routes
  to staff for manual help if appropriate.
* If duplicate requests arrive, the agent should merge them rather than create
  redundant tickets.

Housekeeping Prioritization Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Checkout event or front desk signal marks a room ready for turnover.
2. Housekeeping Dispatch Agent reads ``get_housekeeping_queue``,
   ``get_staff_load_scores``, and ``get_guest_preference_signals`` where
   relevant.
3. The agent computes priority using room readiness impact, expected arrivals,
   late-sleeper preferences, and staff distribution.
4. Staff dashboard displays ranked rooms with rationale.
5. Staff confirms room transitions such as ``mark_room_needs_cleaning`` and
   later ``mark_room_cleaned``.
6. When room becomes available, booking inventory updates automatically.

Failure handling:

* If queue scoring data is stale, fall back to chronological turnover order with
  supervisor override.
* If a room has an unresolved maintenance issue, cleaning completion must not
  unlock availability.

Maintenance Escalation Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Guest reports an issue such as heat, AC noise, broken plumbing, or lighting.
2. Maintenance Triage Agent checks ``get_room_issue_history`` and active room
   state.
3. The agent classifies severity and urgency using ``score_urgency``.
4. If the issue affects habitability or safety, the system proposes
   ``lock_room_for_maintenance`` and may also propose a room change or recovery
   flow.
5. Staff or manager confirms the room lock and maintenance ticket route.
6. Notification Agent updates both guest and staff on next steps.
7. After repair, staff confirms ``release_room_from_maintenance`` and room state
   can progress back toward service readiness.

Failure handling:

* If history shows repeated issues, the case is escalated sooner.
* If the room cannot remain occupied safely, human takeover is mandatory.

Dining And Activity Recommendation Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Guest asks for suggestions or the system detects a good recommendation window.
2. Itinerary and Recommendation Agent loads profile, stay timeline, and
   recommendation candidates.
3. The agent ranks options using ``rank_recommendation_candidates``.
4. Interaction Agent presents a small number of context-rich suggestions, for
   example a quiet dinner after a tiring day or a family activity during a free
   afternoon.
5. Informational suggestions are returned directly.
6. If a suggestion requires reservation or partner booking, the next step is a
   write proposal rather than silent auto-booking.

Failure handling:

* If live partner availability is unknown, the system must label the option as
  requestable rather than confirmed.
* If the guest has declined a category repeatedly, the agent should suppress
  similar nudges for the remainder of the stay.

Complaint Recovery Flow
^^^^^^^^^^^^^^^^^^^^^^^

1. Guest expresses dissatisfaction or the system detects repeated unresolved
   delays.
2. ``score_sentiment`` and service history indicate elevated recovery risk.
3. Sentiment and Recovery Agent reviews open tasks, severity, and policy.
4. If thresholds are met, the system creates a ``create_manager_escalation``
   proposal and an urgent operational notification.
5. Interaction Agent switches tone to empathetic and transparent response mode.
6. A manager or authorized staff member acknowledges the case.
7. If a compensatory action is recommended, it becomes a separate policy-bound
   proposal.
8. Guest receives follow-up until the issue is resolved or handed over fully.

Failure handling:

* If manager delivery fails, retry through alternate urgent channels.
* If compensation policy is unclear, block autonomous promises and route to human
  review.

Checkout Flow
^^^^^^^^^^^^^

1. Guest requests checkout or the departure window begins.
2. Guest Reception and Check-In Agent reviews reservation status, open service
   requests, and payment state.
3. If checkout can proceed, the system proposes ``register_guest_checkout``.
4. After confirmation, reservation becomes ``CHECKED_OUT`` and room turnover is
   triggered.
5. Housekeeping Dispatch Agent queues the room for cleaning.
6. Notification Agent sends a completion or thank-you message.

Failure handling:

* If open charges or unresolved service incidents remain, the system surfaces the
  blocker and routes to staff.
* If the guest exits physically without digital checkout, staff can complete the
  process later with an authenticated action.

Post-Stay Memory Retention Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. After checkout, Memory Update Agent scans stay transcript, service history,
   and recommendation interactions.
2. ``summarize_memory_delta`` produces candidate long-term signals.
3. Signals meeting confidence threshold are written to guest preference memory.
4. Ambiguous or one-off signals remain in session memory or are discarded.
5. Analytics and audit systems receive privacy-safe summary events.

Failure handling:

* If memory scoring confidence is low, do not promote the preference.
* Sensitive data categories must be explicitly excluded from durable memory.

Proactive Nudge Flow
^^^^^^^^^^^^^^^^^^^^

1. Scheduler or event-driven trigger checks stay context and guest preferences.
2. Itinerary and Recommendation Agent looks for a meaningful opportunity, such
   as dinner timing, weather shift, spa availability, or transport reminder.
3. ``detect_policy_conflicts`` ensures the nudge is allowed and not excessive.
4. Notification Agent sends a low-friction suggestion or the Interaction Agent
   presents it in chat.
5. If the guest engages, the conversation continues into recommendation or
   booking mode.

Failure handling:

* Suppress nudges after repeated non-engagement.
* Never send proactive suggestions during an unresolved critical recovery case.

State Machines
--------------
State machines keep room, reservation, request, and escalation logic aligned.

Room Lifecycle
^^^^^^^^^^^^^^

.. code-block:: text

   AVAILABLE -> BOOKED -> OCCUPIED -> NEEDS_CLEANING -> AVAILABLE

   Any state -> MAINTENANCE_LOCK
   MAINTENANCE_LOCK -> NEEDS_CLEANING or AVAILABLE

Rules:

* Only confirmed booking actions move a room from ``AVAILABLE`` to ``BOOKED``.
* Only validated check-in moves ``BOOKED`` to ``OCCUPIED``.
* Checkout or verified vacancy moves ``OCCUPIED`` to ``NEEDS_CLEANING``.
* Cleaning completion only returns the room to ``AVAILABLE`` if no maintenance
  lock exists.

Reservation Lifecycle
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   PENDING_CONFIRMATION -> CONFIRMED -> CHECKED_IN -> CHECKED_OUT
   PENDING_CONFIRMATION -> CANCELLED
   CONFIRMED -> CANCELLED
   CONFIRMED -> NO_SHOW

Rules:

* Only a confirmed booking write creates ``CONFIRMED``.
* Access issuance does not equal ``CHECKED_IN`` until arrival is validated.
* Checkout and cancellation are terminal for the active stay timeline.

Service Request Lifecycle
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   PENDING -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED
   PENDING -> CANCELLED
   ACKNOWLEDGED -> BLOCKED -> IN_PROGRESS
   IN_PROGRESS -> BLOCKED -> IN_PROGRESS

Rules:

* Guests can create and cancel eligible requests.
* Only staff can move a request into ``IN_PROGRESS`` or ``RESOLVED``.
* Blocked tasks require a reason visible to staff and, when relevant, to the
  guest.

Escalation Lifecycle
^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   DETECTED -> OPEN -> ACKNOWLEDGED -> MITIGATION_IN_PROGRESS -> RESOLVED
   OPEN -> CANCELLED_FALSE_POSITIVE

Rules:

* A critical sentiment or incident signal creates ``DETECTED``.
* Manager acknowledgement is required to move from ``OPEN`` to
  ``ACKNOWLEDGED``.
* Recovery completion requires explicit resolution notes.

Confirmation Proposal Lifecycle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   DRAFTED -> PRESENTED -> CONFIRMED -> EXECUTED
   DRAFTED -> BLOCKED_BY_POLICY
   PRESENTED -> REJECTED
   PRESENTED -> EXPIRED
   CONFIRMED -> EXECUTION_FAILED -> RETRYABLE or MANUAL_REVIEW

Rules:

* Every write proposal has a TTL.
* Double-confirmation must be idempotent.
* Expired proposals cannot be executed.

Notification Lifecycle
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   CREATED -> QUEUED -> SENT -> DELIVERED
                     -> FAILED -> RETRY_QUEUED
                     -> CANCELLED

Rules:

* Urgent staff alerts can retry across channels.
* Guest-facing notifications must dedupe repeated events.

API Inventory And Interface Baseline
------------------------------------
The current architecture should preserve the existing REST baseline while adding
future-ready endpoints for agent runtime and memory features.

Current MVP baseline endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Authentication
  ``POST /api/auth/register``
  ``POST /api/auth/login``

Booking
  ``GET /api/bookings/availability``
  ``POST /api/bookings``
  ``GET /api/bookings/{id}``

Room management
  ``GET /api/rooms``
  ``PUT /api/rooms/{id}/status``

Guest services
  ``POST /api/services/requests``
  ``GET /api/services/requests``
  ``PUT /api/services/requests/{id}/status``

Future-ready endpoint families
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Agent runtime
  ``POST /api/agent/intents``
  ``POST /api/agent/proposals/{proposal_id}/confirm``
  ``POST /api/agent/proposals/{proposal_id}/cancel``

Notifications
  ``GET /api/notifications``
  ``POST /api/notifications/send``

Memory and profile
  ``GET /api/guests/{id}/profile``
  ``GET /api/guests/{id}/preferences``
  ``POST /api/guests/{id}/preferences/recompute``

Recommendations
  ``GET /api/recommendations``
  ``POST /api/recommendations/propose-booking``

Escalations
  ``GET /api/escalations``
  ``POST /api/escalations``
  ``PUT /api/escalations/{id}/status``

Safety, Governance, And Operations
----------------------------------
The system must be safe not because the model is trusted, but because the
architecture assumes the model can be wrong.

Role-Based Access Control
^^^^^^^^^^^^^^^^^^^^^^^^^

* ``Guest`` can query own booking context, create eligible service requests,
  confirm own booking and service proposals, and receive notifications.
* ``Staff`` can view operational queues, update task status, confirm room-state
  changes, and acknowledge escalations within role boundaries.
* ``Admin`` or management can override policies, approve refunds, manage severe
  escalations, and inspect audit history.

Propose-Then-Confirm Rules
^^^^^^^^^^^^^^^^^^^^^^^^^^

* All agent-initiated writes are proposal-based.
* The confirming actor must match the risk and domain of the action.
* Proposal TTL should be short for operational tasks and longer for booking
  decisions.
* A proposal must present the action in human language plus the structured
  impact scope.

Auditability
^^^^^^^^^^^^

Every agent-assisted action must emit an audit event with:

* Timestamp
* Actor role and authenticated identity when present
* Agent name and model/runtime version
* Tool name
* Sanitized reason and scope
* Confirmation result
* Execution outcome

No raw payment data, full access credentials, or unnecessary transcript content
should be stored in general-purpose logs.

Low-Connectivity Behavior
^^^^^^^^^^^^^^^^^^^^^^^^^

The platform must degrade gracefully when connectivity is inconsistent.

* Guest channels should support retryable request submission and status polling.
* Staff dashboards should tolerate short disconnections and resync queue state.
* Access issuance should always have a manual fallback path.
* Notification delivery should support delayed send and alternate channels.
* Read-heavy knowledge responses can use cached data with visible staleness
  guards.

Retry And Idempotency
^^^^^^^^^^^^^^^^^^^^^

* Every write tool must accept an idempotency key.
* Duplicate confirmations must never create duplicate bookings, tickets, or
  refunds.
* External connector calls must reconcile asynchronous completion through
  status-check or webhook flows.
* Retry logic must be policy-aware so urgent alerts retry more aggressively than
  low-priority nudges.

Human Takeover
^^^^^^^^^^^^^^

Human handover is required when:

* Policy blocks an action.
* The model confidence is too low for a safe automated interpretation.
* A guest is highly dissatisfied.
* A room safety or severe maintenance issue is detected.
* A payment or access-control action fails in a way that strands the guest.

When handover occurs, the system should pass a concise summary to staff:
intent, context, attempted actions, open proposals, and outstanding risks.

Multilingual Support
^^^^^^^^^^^^^^^^^^^^

The guest experience should eventually support English, Amharic, and additional
languages relevant to the property mix.

* Conversation should preserve tone across translation.
* Service request types must map to one shared canonical domain regardless of
  input language.
* Low-confidence translations should trigger clarification or staff assistance.

Observability
^^^^^^^^^^^^^

The system should expose the following operational metrics:

* Booking conversion rate from chat-assisted discovery.
* Median response time for guest service requests.
* Time from negative sentiment detection to human acknowledgment.
* Room turnover time and queue aging.
* Proposal confirmation rate and expiration rate.
* Notification delivery success rate by channel.
* Memory signal promotion accuracy and correction rate.

Privacy And Data Minimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Durable guest memory must store preference signals, not raw transcripts by
  default.
* Sensitive categories should be excluded or require explicit policy approval.
* Staff views should surface only the data required for service delivery.

Phased Rollout Guidance
-----------------------
The architecture should be implemented in phases so the team can deliver value
quickly without overcommitting the first release.

Phase 1: Core concierge and operations MVP
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Guest chat interface for booking help, inquiries, and basic service requests.
* Modular monolith with auth, bookings, rooms, and guest services.
* Interaction Agent, Planner Orchestrator, Booking Agent, Service Request Agent,
  Guest Reception and Check-In Agent, and basic Notification Agent.
* READ and WRITE tools for bookings, room state, and service requests.
* Sentiment scoring for alerting, even if recovery workflows remain manual.

Phase 2: Operational intelligence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Housekeeping Dispatch Agent and Maintenance Triage Agent.
* Staff load scoring and queue prioritization.
* Proposal store, audit events, and richer notification lifecycle.
* Better check-in and checkout workflows.

Phase 3: Personalization and recovery
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Durable guest preference memory.
* Itinerary and Recommendation Agent.
* Sentiment and Recovery Agent with escalation case management.
* Recommendation ranking and proactive nudges.

Phase 4: Ecosystem integrations and multi-property maturity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Payment gateway integration.
* PMS or channel manager sync where needed.
* Partner experience booking connectors.
* Multi-property analytics, policy templates, and shared model governance.

Acceptance Checklist For This Specification
-------------------------------------------
This document is complete only if the implementation and review process can
answer "yes" to the following:

* Does every major user journey define the guest input, agent routing, tool
  usage, state changes, confirmation path, and failure behavior?
* Are room, reservation, service request, escalation, proposal, and
  notification states explicit?
* Are all write actions protected by a clear confirmation and policy model?
* Are the current PRD and system design baseline decisions preserved?
* Are future-ready extensions clearly separated from current MVP commitments?
* Are audit, privacy, retry, and human-handover rules part of the architecture,
  not afterthoughts?

Conclusion
----------
HabitaLife should be built as an agentic hospitality operating system, not as a
generic chatbot. The correct architecture is a layered platform where natural
language understanding sits on top of deterministic tools, shared domain state,
and strong human-governed safety rails. That combination lets HabitaLife deliver
personalized guest experiences, faster staff coordination, and operational
visibility without depending on expensive smart-room infrastructure.
