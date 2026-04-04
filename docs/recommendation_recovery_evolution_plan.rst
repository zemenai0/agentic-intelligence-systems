Recommendation, Recovery, And Memory Evolution Plan
===================================================

Purpose
-------
This document defines the next-stage architecture for HabitaLife's
recommendation engine and its surrounding feedback loops.

It is a cross-cutting design and implementation plan, not an API-only note.
It spans:

* ``POST /internal/agent/recommend``
* ``POST /internal/agent/sentiment/score``
* ``POST /internal/agent/memory/summarize``
* backend-owned proposal execution, notification delivery, and audit logging
* durable and session memory models already described in the contract design

This plan is anchored to the current live implementation in this repository and
proposes phased, additive evolution rather than a clean-slate rewrite.

Related Documents
-----------------
This plan should be read with:

* :doc:`api/agent_private_contract_v1`
* :doc:`contract_design_plan`
* :doc:`agentic_concierge_specification`
* :doc:`backend_frontend_integration_plan`

Purpose And Current State
-------------------------
The current recommendation, sentiment, and memory surfaces are intentionally
lightweight. They work, but they do not yet form the richer learning and
recovery loop described in the broader concierge specification.

Current ``RecommendationAgent.recommend(...)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The current recommendation path is implemented in
``src/agentic_intelligence_systems/agents/recommendation.py``.

Current behavior:

* calls ``BackendAPIClient.get_service_catalog(...)``
* loads service categories and service catalog items from the backend
* ranks catalog items with a simple heuristic:

  * strong boost if the requested category matches the service category
  * otherwise a decreasing confidence score by list position

* returns ``RecommendResponse`` with ranked ``RecommendationItem`` values
* does not currently enrich the response with explanations, suppression
  metadata, itinerary bundling, or recovery context

Current limitations:

* recommendation is service-catalog-centric, not itinerary-centric
* ranking is mostly category-based rather than deeply contextual
* ``recommendation_scope.time_window`` is accepted by contract but is not
  materially used by ranking
* ``booking_context.resort_id`` is accepted by contract but is currently not
  used as a strong backend filter in the recommendation path
* the current ``ServiceCatalogItem`` model does not include richer safety,
  crowding, or operational eligibility details

Current ``SentimentAgent.score(...)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The current sentiment path is implemented in
``src/agentic_intelligence_systems/agents/sentiment.py``.

Current behavior:

* scores one message at a time
* uses a small heuristic lexicon of positive and negative terms
* produces:

  * sentiment label
  * numeric score
  * severity
  * ``handover_required`` flag

* supports fast service-risk triage for the current turn only

Current limitations:

* sentiment is message-level, not trend-level
* no weighting by unresolved service delays, repeated complaints, or room issue
  history
* no grievance summary for staff
* no recovery-offer recommendation output
* no suppression signal for normal upsell activity during active recovery

Current ``MemorySummarizer.summarize(...)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The current memory path is implemented in
``src/agentic_intelligence_systems/memory/summarizer.py``.

Current behavior:

* concatenates supplied messages into one summary string
* creates a ``MemorySnapshot`` with ``scope="stay"``
* extracts a small number of heuristic signals such as:

  * quiet dining
  * late housekeeping
  * vegetarian or vegan preference

* returns candidate signals and a lightweight ``structured_memory_json``

Current limitations:

* summarization is lightweight and not yet used as a ranking loop
* no distinction in behavior between session memory, stay memory, and durable
  profile promotion logic
* no confidence-based promotion policy beyond the returned signal confidence
* no sensitivity tagging, expiry hints, or promotion scope metadata

Current Boundary
^^^^^^^^^^^^^^^^
The current repository correctly keeps the core system boundary intact:

* agent service owns reasoning, ranking, and proposal drafting
* backend owns execution, persistence, policy enforcement, notifications, and
  audit truth

That boundary should remain unchanged as these capabilities deepen.

Target Architecture
-------------------
The target system is a unified loop rather than three isolated helpers.

Unified Recommendation, Recovery, And Memory Loop
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The intended processing loop is:

1. context ingestion
2. candidate generation
3. eligibility pruning
4. ranking and bundling
5. recovery-aware suppression or recovery-offer generation
6. proposal drafting where confirmation or execution is needed
7. memory promotion and memory decay decisions
8. audit and event logging in backend-owned stores

Recommended responsibility split:

* agent service:

  * interprets guest intent and timing
  * ranks candidates
  * generates rationales
  * decides whether a recommendation should be informational, proposal-based,
    or suppressed

* backend:

  * provides operational read models
  * executes proposals
  * persists ``proposal_action`` and notification state
  * owns escalation lifecycle and policy enforcement

Data Inputs For The Unified Loop
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The target loop should ingest the following input families:

* actor context and booking context
* stay timeline and arrival/departure window
* resort and service catalog data
* operational availability and capacity signals
* open service requests and SLA age
* guest preference memory and session memory
* sentiment trend and unresolved-friction signals
* weather and environmental context
* business rules such as nudge frequency, safety filters, and compensation
  policy

Recommendation Engine Evolution
-------------------------------
The recommendation engine should evolve from simple catalog sorting into a
constraint-aware ranking system with explainable outputs.

Five Score Families
^^^^^^^^^^^^^^^^^^^
Each candidate should receive separate component scores before final ranking.

1. Situational fit
   How well the option fits the guest's immediate context.

   Inputs:

   * time of day
   * stay phase
   * weather
   * current open schedule window
   * family or solo context

2. Preference fit
   How well the option matches durable or recent memory.

   Inputs:

   * ``guest_preference_signal``
   * recent ``conversation_memory_snapshot``
   * repeated past choices
   * explicit likes and dislikes

3. Operational fit
   How feasible and operationally wise the option is right now.

   Inputs:

   * occupancy and crowding
   * service slot capacity
   * staff load
   * service availability
   * room and stay state

4. Recovery fit
   Whether the option is safe or beneficial under current dissatisfaction or
   friction conditions.

   Inputs:

   * sentiment trend
   * open incidents
   * service delay severity
   * active escalation or recovery case

5. Business and novelty fit
   A bounded commercial and variety score.

   Inputs:

   * cross-sell suitability
   * freshness relative to prior recommendations
   * avoidance of repeated ignored nudges

Required Input Signals
^^^^^^^^^^^^^^^^^^^^^^
The ranking layer should be able to consume:

* stay timeline
* booking state
* resort and service catalog
* weather context
* occupancy and load context
* open service request and SLA context
* memory signals from ``guest_preference_signal``
* short-term summaries from ``conversation_memory_snapshot``

Hard Filters Before Ranking
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Before scoring, the engine should exclude candidates that violate hard rules:

* service constraints and safety eligibility
* unavailable, oversubscribed, or operationally blocked offers
* repeated declines or nudge fatigue for the same category
* active critical recovery cases that should suppress normal upsell behavior

These filters should happen before ranking so the engine never presents an
unsafe or clearly inappropriate option just because it scored well elsewhere.

Collaborative Filtering And Cohort Signals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Collaborative filtering should be introduced carefully and framed as
behavior-first cohorting.

Allowed weak priors:

* language
* locale
* travel party type
* explicit stay purpose
* repeated behavior clusters
* family context
* booking-window and timing patterns

Disallowed direct ranking signals:

* protected or sensitive demographic inference
* direct nationality targeting as the primary recommendation driver
* raw ethnicity, religion, or similar sensitive identity proxies

The system may use area or locale only as a weak, secondary prior when it is
already present in trusted business context and when it is clearly subordinate
to individual behavior, explicit preferences, and current stay conditions.

Bundled And Itinerary-Style Recommendations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ranking system should evolve beyond flat lists into structured bundles such
as:

* perfect-day bundles
* quiet-evening dinner plus spa combinations
* room plus add-on service bundles
* recovery-safe substitutions when a preferred option is unsuitable

These bundles should remain informational unless a downstream step requires a
proposal for booking or guaranteed service allocation.

Sentiment And Recovery Evolution
--------------------------------
The recovery layer should move from turn-level sentiment scoring to operational
recovery intelligence.

Trend-Aware Sentiment
^^^^^^^^^^^^^^^^^^^^^
Future sentiment scoring should incorporate:

* rolling conversation trend
* unresolved-delay weighting
* recurrence weighting
* room and service incident history weighting

Examples:

* a mildly negative message may become high severity if the guest has waited
  too long for a pending request
* repeated complaints about heat, noise, or housekeeping should increase
  recovery urgency even if each single message is polite

Recovery Outputs
^^^^^^^^^^^^^^^^
The evolved recovery layer should be able to produce:

* manager escalation recommendation
* recovery-offer recommendation
* tone adaptation flag for guest-facing reply generation
* suppression of normal upsells during active recovery

Compensatory actions must remain proposal-based and policy-bound. The agent may
recommend them, but the backend remains the final authority for execution.

Operational Recovery Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Examples of recovery-aware behavior:

* a delayed towels request plus negative sentiment increases escalation
  priority
* a complaint about room heat can lead to a recovery suggestion, an AC-focused
  memory signal, and a future room-assignment preference
* a critical unresolved incident suppresses proactive dining or spa nudges

Memory Feedback Loop
--------------------
The memory system should become an explicit input into recommendation and
recovery rather than a disconnected summarization helper.

Three Memory Layers
^^^^^^^^^^^^^^^^^^^
The system should distinguish:

* session memory
  recent dialogue context, temporary references, and current goals
* stay memory
  behavior and constraints that matter for the current booking or active stay
* durable preference memory
  repeated, high-confidence, non-sensitive patterns that survive across stays

Promotion Rules
^^^^^^^^^^^^^^^
Signals should be promoted into durable memory only when they are:

* repeated
* high-confidence
* non-sensitive
* useful across stays

Good promotion examples:

* quiet-room preference
* breakfast time preference
* AC sensitivity or heat sensitivity
* family-safe activity preference
* late housekeeping preference

Signals that should usually stay temporary:

* one-off mood
* transient annoyance without repetition
* scheduling choices that appear accidental rather than intentional

Negative Memory Use
^^^^^^^^^^^^^^^^^^^
Negative experience signals should influence future behavior carefully.

Examples:

* repeated AC complaints can alter future room recommendation and room
  assignment reasoning
* repeated preference for quiet dining can shift evening suggestions
* repeated refusal of crowded activities can suppress those categories

Raw Transcript Ban
^^^^^^^^^^^^^^^^^^
Durable memory must never store raw transcript bodies. Durable stores should
keep only structured, privacy-scoped signals and confidence metadata.

Phased Contract Extensions
--------------------------
These are proposed additive extensions to the current private contracts. They
should remain optional and backward-compatible until adopted.

``RecommendRequest`` Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Add optional fields:

* ``conversation_id``
* ``trigger_context``
* ``operational_context``
* ``weather_context``
* ``preference_snapshot``

Recommended intent:

* ``conversation_id`` gives the ranking call access to short-term context
* ``trigger_context`` explains whether the recommendation was user-initiated,
  scheduler-initiated, recovery-initiated, or upsell-initiated
* ``operational_context`` provides occupancy, slot, and staffing signals
* ``weather_context`` supports environmental pivots
* ``preference_snapshot`` allows backend to provide a summarized memory view
  without requiring new round-trips

``RecommendResponse`` Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Add optional fields:

* ``explanations``
* ``suppressed_candidates``
* ``next_best_actions``

Recommended intent:

* ``explanations`` supplies ranking reasons for staff and audit use
* ``suppressed_candidates`` explains what was filtered and why
* ``next_best_actions`` lets backend or frontend present the next likely step

``SentimentRequest`` Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Add optional fields:

* ``recent_messages``
* ``open_service_state``
* ``booking_status``

Recommended intent:

* trend-aware scoring across several turns
* delay-aware severity
* state-aware recovery decisions

``SentimentResponse`` Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Add optional fields:

* ``trend_score``
* ``grievance_summary``
* ``recommended_recovery_action``

Recommended intent:

* expose longer-term dissatisfaction trajectory
* summarize the likely grievance for staff
* suggest policy-bound recovery options without auto-executing them

``CandidateSignal`` Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Add optional fields:

* ``promotion_scope``
* ``expiry_hint``
* ``sensitivity_class``

Recommended intent:

* show whether a signal belongs in session, stay, or durable memory
* indicate when temporary signals should expire
* classify sensitivity so backend can enforce storage rules

These should be documented as private internal contract evolutions, not
frontend-facing APIs.

Backend And Data Dependencies
-----------------------------
The design should explicitly tie into existing or planned backend models.

Existing And Planned Data Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The recommendation and recovery loop should build on:

* ``guest_preference_signal``
* ``conversation_memory_snapshot``
* ``proposal_action``
* ``notification``
* ``escalation_case``

New Read-Model Needs
^^^^^^^^^^^^^^^^^^^^
The following read models are recommended without requiring immediate schema
writes in this repository:

* weather snapshot
* occupancy and load snapshot
* service constraints snapshot
* open-request SLA summary

Auditability
^^^^^^^^^^^^
``proposal_action`` should be reused to record:

* proactive recommendations that required confirmation
* recovery offers
* suppression decisions that materially affected guest experience

The goal is not to log every ranking intermediate, but to ensure that
guest-visible or staff-visible actions remain auditable.

Operational Safety And Privacy
------------------------------
The following rules should govern the evolved system:

* no silent guaranteed bookings from recommendation
* no promotional nudges during unresolved critical recovery cases
* no durable storage of sensitive raw text
* no direct sensitive demographic targeting
* degraded mode and offline-cache behavior for low-bandwidth resorts

Offline And Degraded Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When real-time context is unavailable:

* use cached catalog and baseline operational data if available
* clearly downgrade confidence internally
* present only safe, non-guaranteed recommendations
* avoid promises that depend on live external confirmation

Phased Delivery Plan
--------------------
Phase 1: Enrich Current Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Focus:

* improve ranking inputs using current endpoints
* enrich current recommendation response semantics

Recommended work:

* use ``time_window`` meaningfully
* use ``resort_id`` as a stronger filter
* enrich recommendation reasoning
* connect current memory outputs into ranking as soft features

Phase 2: Add Trend-Aware Recovery
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Focus:

* add trend-aware sentiment outputs
* add recovery recommendation outputs
* connect memory and recovery more tightly

Recommended work:

* extend sentiment inputs with recent transcript and SLA context
* add grievance summaries and recovery recommendations
* feed negative-memory candidates into future ranking decisions

Phase 3: Proactive And Operationally Aware Personalization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Focus:

* proactive nudges
* itinerary bundles
* cohort priors
* operational load balancing

Recommended work:

* scheduler-triggered recommendation windows
* family-safe and recovery-safe bundled suggestions
* behavior-first cohort priors
* occupancy-aware ranking and delivery timing

Validation Scenarios
--------------------
The evolved system should be validated with scenarios such as:

* guest asks for dining, spa, or activity suggestions during a weather change
* family booking suppresses unsafe or age-ineligible activities
* quiet-evening preference shifts dining recommendation and timing
* negative sentiment plus delayed service request triggers recovery instead of
  an upsell
* repeated AC complaint becomes a memory signal and changes future stay
  recommendations
* existing critical recovery case suppresses proactive nudges
* offline or degraded external context falls back to cached, base
  recommendations
* cohort logic uses behavior-first priors without direct sensitive demographic
  targeting
* proactive offers and recovery proposals remain auditable through backend
  records

Assumptions And Defaults
------------------------
This plan assumes:

* the document lives in ``docs/`` because it is architectural and
  cross-cutting
* the work is kept as one unified spec rather than split into separate
  recommendation, recovery, and memory documents
* collaborative filtering is treated as behavior-first cohorting with privacy
  limits
* the evolution remains phased and additive
* no code changes are implied by this document alone; implementation follows in
  later tasks
