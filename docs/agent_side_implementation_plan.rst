HabitaLife Agent Side: Implementation Plan
==========================================

Purpose
-------
This document defines how to implement the agent side of HabitaLife in this
repository now that:

* the backend engineer owns the public and internal APIs
* the contract documents have been drafted
* the backend schema extensions have been shared

The goal is to turn this repository from a scaffold into a working private
agent service that integrates cleanly with the backend.

Implementation Goal
-------------------
The first implementation milestone is a private FastAPI service that can:

* receive backend requests through the private agent contract
* classify guest intent
* call backend-owned internal read tools
* generate assistant responses
* draft proposals for write actions
* return safe fallbacks or human-handover decisions when confidence is low

This repo should not own canonical business state. It should own reasoning,
planning, routing, sentiment, and memory summarization.

Recommended Stack
-----------------
The recommended stack for the agent side is:

Runtime
^^^^^^^

* Python 3.12
* FastAPI for the private HTTP service
* Uvicorn for local and container serving
* Pydantic v2 style models for request and response contracts
* ``httpx`` async client for backend internal API calls

LLM And Agent Layer
^^^^^^^^^^^^^^^^^^^

* provider adapter pattern for model calls so we can swap OpenAI or other
  providers later
* one thin orchestration layer instead of a heavy framework in v1
* structured outputs validated by Pydantic

Reliability And Observability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* standard structured logging
* request and trace IDs passed through every layer
* retry wrapper for backend tool calls and LLM calls where safe
* metrics hooks for latency, tool failures, and handover rate

Testing
^^^^^^^

* ``pytest``
* ``pytest-asyncio``
* HTTP client mocking for backend API tests
* contract tests for request and response schema validation

What Not To Add In V1
^^^^^^^^^^^^^^^^^^^^^

* no database owned by the agent service
* no direct writes to backend business tables
* no complex multi-agent framework before the first orchestration loop works
* no vector database inside this repo until the memory API contract is stable

Recommended Project Layout
--------------------------
The current package scaffold can be turned into this structure:

.. code-block:: text

   src/agentic_intelligence_systems/
     api/
       app.py
       routes.py
       dependencies.py
     contracts/
       private_api.py
       tools.py
       common.py
     agents/
       interaction.py
       planner.py
       booking.py
       service_request.py
       guest_reception.py
       sentiment.py
       recommendation.py
       memory.py
     orchestration/
       responder.py
       handover.py
       policies.py
     clients/
       backend_api.py
       llm_provider.py
     prompts/
       system/
       templates/
     memory/
       summarizer.py
       mappers.py
     observability/
       logging.py
       metrics.py
     config.py

Recommended Mapping To Existing Repo
------------------------------------
The current scaffold already gives us the right top-level areas:

* use ``src/agentic_intelligence_systems/agents`` for specialized agent modules
* use ``src/agentic_intelligence_systems/memory`` for summarization and signal
  mapping
* use ``src/agentic_intelligence_systems/tools`` for internal tool abstractions
* use ``src/agentic_intelligence_systems/prompts`` for prompt templates and
  structured output instructions
* add ``contracts``, ``clients``, ``api``, and ``orchestration`` packages

Implementation Phases
---------------------

Phase 1: Service Skeleton
^^^^^^^^^^^^^^^^^^^^^^^^^
Goal:
  Stand up the private FastAPI service and freeze internal code boundaries.

Tasks:

* create FastAPI application entrypoint
* create health endpoint
* create config model and environment variable loading
* add request ID and trace ID middleware
* create base logging utilities
* add dependency placeholders for backend client and LLM provider

Deliverable:

* service boots locally and exposes health plus placeholder private routes

Phase 2: Contract Models
^^^^^^^^^^^^^^^^^^^^^^^^
Goal:
  Encode the private contracts as strict Python models.

Tasks:

* create Pydantic models for common envelopes
* create models for ``/internal/agent/respond``
* create models for ``/internal/agent/recommend``
* create models for ``/internal/agent/sentiment/score``
* create models for ``/internal/agent/memory/summarize``
* create models for tool request and response envelopes
* create proposal and handover models

Deliverable:

* validated contract layer shared across routes, agents, and tests

Phase 3: Backend Tool Client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Goal:
  Let the agent service read trusted backend state through internal APIs.

Tasks:

* implement async backend client
* add methods for:
  ``get_current_stay_context``
  ``search_room_inventory``
  ``get_booking_record``
  ``get_check_in_readiness``
  ``get_room_status_snapshot``
  ``get_service_catalog``
* add retry rules and timeout handling
* map backend errors into stable internal exceptions

Deliverable:

* one client abstraction used everywhere instead of scattered HTTP calls

Phase 4: First MVP Agent Flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Goal:
  Ship one end-to-end vertical slice through ``/internal/agent/respond``.

Recommended first scenario:

* guest asks for an in-stay service request like extra towels

Tasks:

* implement basic intent classifier
* implement planner that chooses read tools and one domain agent
* implement ``ServiceRequestAgent``
* fetch stay context and service catalog from backend
* generate assistant response
* draft ``create_service_request`` proposal
* return response in the private contract format

Deliverable:

* backend can call one real working agent route for service-request proposals

Phase 5: Additional MVP Flows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Goal:
  Expand from one vertical slice to a useful MVP agent surface.

Recommended next flows:

* booking lookup
* room availability and booking guidance
* check-in readiness guidance
* basic FAQ or policy lookup

Tasks:

* implement ``BookingAgent``
* implement ``GuestReceptionCheckInAgent``
* implement lightweight ``SearchKnowledgeAgent``
* implement plain-answer path with no proposal
* implement clarification path for incomplete inputs
* implement handover path for blocked or low-confidence cases

Deliverable:

* a useful private agent service that covers the first operational journeys

Phase 6: Sentiment And Memory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Goal:
  Add the first non-trivial intelligence features after the core request loop is
  stable.

Tasks:

* implement ``/internal/agent/sentiment/score``
* implement ``/internal/agent/memory/summarize``
* map transcript chunks into ``conversation_memory_snapshot``-style outputs
* map candidate durable preferences into ``guest_preference_signal`` outputs
* define thresholds for handover and promotion

Deliverable:

* backend can use the agent for recovery and memory summarization workflows

Initial Agent Set
-----------------
The recommended initial agent set is intentionally smaller than the full vision
in the architecture doc.

Build first:

* ``InteractionAgent``
* ``PlannerOrchestrator``
* ``ServiceRequestAgent``
* ``BookingAgent``
* ``GuestReceptionCheckInAgent``

Add next:

* ``SearchKnowledgeAgent``
* ``SentimentRecoveryAgent``
* ``MemoryUpdateAgent``

Delay until later:

* ``HousekeepingDispatchAgent``
* ``MaintenanceTriageAgent``
* ``RecommendationAgent`` with richer ranking

Reason:

* the first set is enough to support message understanding, booking support,
  service requests, and arrival flows
* the later set depends more heavily on backend staffing, queue, escalation, and
  memory maturity

Detailed Task Breakdown
-----------------------
These tasks are ordered to reduce rework.

Task Group A: Foundation
^^^^^^^^^^^^^^^^^^^^^^^^

* add runtime dependencies to ``requirements/base.txt`` and package metadata
* implement ``config.py`` with environment settings
* add ``api/app.py`` and service bootstrap
* add base logging and middleware
* add container run command for local service execution

Task Group B: Contracts
^^^^^^^^^^^^^^^^^^^^^^^

* create ``contracts/common.py``
* create ``contracts/private_api.py``
* create ``contracts/tools.py``
* mirror the structures in
  ``docs/api/agent_private_contract_v1.rst`` and
  ``docs/api/tool_contract_catalog_v1.rst``

Task Group C: Backend Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* create ``clients/backend_api.py``
* add auth and request header handling for private backend calls
* add read-tool methods
* add typed error mapping
* add test doubles for backend responses

Task Group D: LLM Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* create ``clients/llm_provider.py``
* implement one provider adapter
* add structured output parsing helpers
* create prompt templates for intent classification, response drafting, and
  proposal drafting

Task Group E: Orchestration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* create ``orchestration/responder.py``
* create routing logic from intent to domain agent
* implement proposal-only write policy
* implement fallback and handover decisions

Task Group F: Domain Agents
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* implement ``agents/service_request.py``
* implement ``agents/booking.py``
* implement ``agents/guest_reception.py``
* implement ``agents/sentiment.py`` after MVP routes are stable
* implement ``agents/memory.py`` after transcript flow is stable

Task Group G: Tests
^^^^^^^^^^^^^^^^^^^

* unit tests for contract models
* unit tests for planner routing
* unit tests for proposal drafting
* integration tests for backend client behavior
* end-to-end tests for the first response flow

Task Group H: Developer Experience
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* add local run instructions to README
* add sample `.env` documentation
* add test commands
* add example request payloads for backend team

Suggested Runtime Dependencies
------------------------------
These are the likely runtime packages to add once implementation starts:

* ``fastapi``
* ``uvicorn[standard]``
* ``httpx``
* ``pydantic``
* ``pydantic-settings``
* ``tenacity``

Likely test dependencies to add:

* ``pytest-asyncio``
* ``respx`` or equivalent HTTP mocking tool

Observability And Safety
------------------------
The following guardrails should exist from the first implementation:

* request IDs and trace IDs in every route and client call
* strict input and output validation with Pydantic
* timeout limits on backend and model calls
* no agent-side direct business writes
* proposal-only write drafting
* explicit handover result for low confidence or backend unavailability

Recommended First Sprint
------------------------
If we want the fastest useful result, the first sprint should aim for:

* FastAPI service boots
* private contract models are implemented
* backend client can call two or three read tools
* ``/internal/agent/respond`` supports one real scenario:
  service request proposal generation
* tests exist for that scenario

Definition Of Done For MVP Agent V1
-----------------------------------
The first meaningful version is complete when:

* backend can call ``/internal/agent/respond`` successfully
* the agent can read stay context and service catalog from backend
* the agent returns safe proposal drafts for write actions
* the agent never performs direct backend writes
* low-confidence or backend-failure paths return a handover-ready response

Decisions Needed Before Coding
------------------------------
These are the details we still need from you before implementation should begin.

1. LLM provider
^^^^^^^^^^^^^^^

Needed answer:
  Which model provider should we target first for the agent service?

Recommended default:
  OpenAI-compatible provider adapter with one primary model for reasoning and a
  lighter one later for classification. primary model could be gemini pro(vertex ai)

2. Backend private API base details
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Needed answers:

* exact base URL pattern for backend internal APIs
* how the agent authenticates to backend private APIs
* whether tool calls are generic or route-specific

Examples we need confirmed:

* ``POST /internal/tools/get_current_stay_context``
* or ``GET /internal/bookings/{id}/stay-context`` Modern agent systems typically use a hybrid approach: generic tool interface externally and route-specific APIs internally

3. First backend endpoints available
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Needed answers:
  Which internal endpoints will actually exist first?

Minimum set to begin:

* current stay context
* booking record
* check-in readiness
* room inventory search
* service catalog

4. First MVP agent flows
^^^^^^^^^^^^^^^^^^^^^^^^

Needed answer:
  Which flows do you want in the first coded milestone?

Recommended first set:

* service request proposal
* booking lookup
* check-in readiness guidance

5. Agent behavior model
^^^^^^^^^^^^^^^^^^^^^^^

Needed answers:

* do you want one orchestrator with specialized helper modules, or explicit
  per-agent classes from day one?
* do you want prompts and behavior to be strongly separated by agent type?

Recommended default:
  explicit per-agent classes with one shared planner

6. Conversation strategy
^^^^^^^^^^^^^^^^^^^^^^^^

Needed answers:

* will the backend send full recent transcript, or only conversation ID and let
  the agent fetch it?
* how many recent messages should the agent consider in v1?

Recommended default:
  backend sends recent transcript window plus IDs, not the full history

7. Response mode
^^^^^^^^^^^^^^^^

Needed answer:
  Should ``/internal/agent/respond`` be synchronous only in v1, or do you want
  streaming support immediately?

Recommended default:
  synchronous first, streaming second

8. Prompt management
^^^^^^^^^^^^^^^^^^^^

Needed answer:
  Do you want prompts stored as files in this repo or assembled in Python code?

Recommended default:
  prompt files in ``src/agentic_intelligence_systems/prompts``

9. Language scope
^^^^^^^^^^^^^^^^^

Needed answer:
  Should v1 support English only, or English plus Amharic from the start?

Recommended default:
  English first, with multilingual-ready contracts

10. Testing priority
^^^^^^^^^^^^^^^^^^^^

Needed answer:
  Which matters most in the first sprint: contract correctness, end-to-end
  behavior, or prompt quality?

Recommended default:
  contract correctness first, then end-to-end behavior

How To Reply
------------
You can reply with short answers under these headings:

* provider
* backend base URL and auth
* first available internal endpoints
* first MVP flows
* orchestration style
* transcript strategy
* sync or streaming
* prompt storage
* language scope
* testing priority
