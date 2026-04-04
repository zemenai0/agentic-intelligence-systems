HabitaLife Contract Design: Implementation Plan
===============================================

Purpose
-------
This document turns the current HabitaLife architecture specification into a
practical starting plan for contract design across the frontend, backend, and
agent service.

For contract design, the team should treat ``better expriacne v1.sql`` as the
current source of truth because it provides the real enums, entities,
relationships, and foreign-key boundaries in a machine-readable form. The PDF
appears to be a visual rendering of the same schema, but the SQL is more
precise for implementation work.

This plan is derived from:

* the shared backend schema in ``docs/better expriacne v1.sql``
* the platform architecture in ``docs/agentic_concierge_specification.rst``

Goal
----
The goal is not to implement all backend features immediately. The goal is to
freeze the first contract layer that allows three repos or services to move in
parallel:

* frontend applications
* backend public API
* private agent service

Contract Design Outcome
-----------------------
At the end of this effort, the team should have:

* a stable public API contract for frontend-to-backend communication
* a stable private contract for backend-to-agent communication
* a stable internal tool contract for agent-to-backend reads and proposed
  writes
* agreed enums, state transitions, error shapes, and confirmation flows
* a small, explicit backlog of schema changes needed to support the larger
  agentic system

What The Shared Schema Already Gives Us
---------------------------------------
The schema is already strong enough to start designing contracts for the core
hospitality MVP.

Contract-ready domains from the SQL:

* authentication primitives through ``user``, ``session``, ``account``, and
  ``verification``
* resort configuration through ``resort``
* room inventory through ``room``, ``amenity``, ``room_amenity``,
  ``room_image``, and ``room_status_log``
* bookings through ``booking`` and ``booking_audit_log``
* service catalog and paid service scheduling through ``service_category``,
  ``service``, and ``service_booking``
* in-stay operational service requests through ``service_request``
* notification delivery tracking through ``notification``

The SQL also gives us usable enums right now:

* ``room_type``
* ``room_status``
* ``amenity_category``
* ``booking_status``
* ``service_booking_status``
* ``service_request_status``
* ``service_request_type``
* ``notification_channel``
* ``notification_status``
* ``notification_event``

What The Schema Does Not Yet Cover
----------------------------------
The larger concierge specification includes several agentic and operational
concepts that are not yet represented in the schema. These do not block
contract design, but they must be handled deliberately.

Missing or underspecified areas:

* no internal staff profile model separate from ``user`` for privileged access
* no proposal or confirmation entity for the propose-then-confirm flow
* no escalation case model for recovery and manager intervention
* no guest preference memory or conversation memory tables
* no conversation, transcript, or message model for chat history
* no dedicated check-in verification or arrival event model
* no staff shift, workload, or assignment model
* no priority field or SLA field on ``service_request``
* no notification payload model beyond event, channel, and status
* no formal idempotency or request-token persistence model

This means the first contract iteration should separate:

* ``current schema-backed contracts`` that can be designed immediately
* ``future schema extension contracts`` that need backend alignment before
  finalization

Recommended Schema Extensions
-----------------------------
The recommended direction is to keep ``user`` as the universal identity table
for all human accounts and add separate internal-only tables for privileged
staff workflows. In that model:

* a guest is a ``user`` without an ``internal_staff`` row
* a staff member is a ``user`` with an ``internal_staff`` row
* role-based access control is driven from ``internal_staff`` and related staff
  tables, not by overloading the base ``user`` table

The following tables are a practical schema package the backend team can review.
They are designed to fit the current SQL style: text primary keys, PostgreSQL
enums, and foreign keys back to the existing core tables.

1. Internal Staff And Roles
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use this when the team wants to keep guest identities in ``user`` while moving
all internal privileges into a dedicated staff table.

.. code-block:: sql

   CREATE TYPE "internal_staff_role" AS ENUM (
     'front_desk',
     'housekeeping',
     'maintenance',
     'manager',
     'admin'
   );

   CREATE TYPE "internal_staff_status" AS ENUM (
     'active',
     'inactive',
     'suspended'
   );

   CREATE TABLE "internal_staff" (
     "id" text PRIMARY KEY,
     "user_id" text NOT NULL UNIQUE,
     "resort_id" text NOT NULL,
     "employee_code" text UNIQUE,
     "role" internal_staff_role NOT NULL,
     "status" internal_staff_status NOT NULL DEFAULT 'active',
     "is_on_call" boolean NOT NULL DEFAULT false,
     "created_at" timestamp NOT NULL,
     "updated_at" timestamp NOT NULL
   );

   ALTER TABLE "internal_staff"
     ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "internal_staff"
     ADD FOREIGN KEY ("resort_id") REFERENCES "resort" ("id") DEFERRABLE INITIALLY IMMEDIATE;

Recommended rule:

* authorization checks should use ``internal_staff.role`` for internal users
* guests remain plain ``user`` records

2. Guest Preference Memory
^^^^^^^^^^^^^^^^^^^^^^^^^^
This is the durable guest memory table. It stores stable or semi-stable
preference signals that can survive across stays.

.. code-block:: sql

   CREATE TYPE "memory_signal_type" AS ENUM (
     'preference',
     'behavior',
     'constraint',
     'allergy',
     'accessibility',
     'family_context',
     'timing_pattern'
   );

   CREATE TYPE "memory_source_type" AS ENUM (
     'conversation',
     'booking',
     'service_request',
     'service_booking',
     'staff_note',
     'system_inference'
   );

   CREATE TABLE "guest_preference_signal" (
     "id" text PRIMARY KEY,
     "user_id" text NOT NULL,
     "resort_id" text,
     "booking_id" text,
     "signal_type" memory_signal_type NOT NULL,
     "key" text NOT NULL,
     "value_text" text,
     "value_json" jsonb,
     "confidence" numeric(5,4) NOT NULL DEFAULT 0.5000,
     "source_type" memory_source_type NOT NULL,
     "source_ref_id" text,
     "first_seen_at" timestamp NOT NULL,
     "last_seen_at" timestamp NOT NULL,
     "promoted_at" timestamp,
     "is_active" boolean NOT NULL DEFAULT true,
     "created_at" timestamp NOT NULL,
     "updated_at" timestamp NOT NULL
   );

   CREATE INDEX ON "guest_preference_signal" ("user_id", "key");
   CREATE INDEX ON "guest_preference_signal" ("user_id", "is_active");

   ALTER TABLE "guest_preference_signal"
     ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "guest_preference_signal"
     ADD FOREIGN KEY ("resort_id") REFERENCES "resort" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "guest_preference_signal"
     ADD FOREIGN KEY ("booking_id") REFERENCES "booking" ("id") DEFERRABLE INITIALLY IMMEDIATE;

Recommended use:

* store long-lived signals such as quiet-room preference, late-sleeper pattern,
  preferred breakfast time, family travel context, or mobility constraints
* do not store raw transcripts here

3. Conversation Memory Snapshots
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is short- to medium-term memory tied to one active conversation or stay.
It stores agent-ready summaries, not raw messages.

.. code-block:: sql

   CREATE TYPE "conversation_memory_scope" AS ENUM (
     'session',
     'stay',
     'profile'
   );

   CREATE TABLE "conversation_memory_snapshot" (
     "id" text PRIMARY KEY,
     "user_id" text,
     "booking_id" text,
     "conversation_id" text,
     "scope" conversation_memory_scope NOT NULL,
     "summary_text" text NOT NULL,
     "structured_memory_json" jsonb,
     "confidence" numeric(5,4) NOT NULL DEFAULT 0.5000,
     "source_message_start_id" text,
     "source_message_end_id" text,
     "created_at" timestamp NOT NULL,
     "expires_at" timestamp
   );

   CREATE INDEX ON "conversation_memory_snapshot" ("conversation_id", "created_at");
   CREATE INDEX ON "conversation_memory_snapshot" ("user_id", "scope");

Recommended use:

* session memory for pronouns, recent requests, and temporary context
* stay memory for stay-specific behavior that matters until checkout
* profile memory as a summarized bridge into durable preference promotion

4. Conversations, Transcripts, And Messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Yes, for an agentic concierge you should add chat persistence tables. Without
them, the backend cannot reliably support transcript retrieval, handover,
assistant replay, conversation-scoped memory, or message-level audit.

Minimum recommended model:

.. code-block:: sql

   CREATE TYPE "conversation_channel" AS ENUM (
     'mobile_chat',
     'web_chat',
     'kiosk',
     'staff_console'
   );

   CREATE TYPE "conversation_status" AS ENUM (
     'open',
     'handover',
     'closed',
     'archived'
   );

   CREATE TYPE "conversation_message_role" AS ENUM (
     'guest',
     'assistant',
     'staff',
     'system',
     'tool'
   );

   CREATE TYPE "conversation_message_type" AS ENUM (
     'text',
     'event',
     'tool_call',
     'tool_result',
     'summary'
   );

   CREATE TABLE "conversation_thread" (
     "id" text PRIMARY KEY,
     "guest_user_id" text,
     "session_id" text,
     "booking_id" text,
     "resort_id" text,
     "channel" conversation_channel NOT NULL,
     "status" conversation_status NOT NULL DEFAULT 'open',
     "language" text,
     "started_at" timestamp NOT NULL,
     "last_message_at" timestamp NOT NULL,
     "closed_at" timestamp,
     "metadata_json" jsonb
   );

   CREATE TABLE "conversation_message" (
     "id" text PRIMARY KEY,
     "conversation_id" text NOT NULL,
     "sender_role" conversation_message_role NOT NULL,
     "sender_user_id" text,
     "message_type" conversation_message_type NOT NULL DEFAULT 'text',
     "content_text" text,
     "content_json" jsonb,
     "language" text,
     "translated_from" text,
     "reply_to_message_id" text,
     "tool_name" text,
     "tool_call_id" text,
     "related_entity_type" text,
     "related_entity_id" text,
     "created_at" timestamp NOT NULL
   );

   CREATE INDEX ON "conversation_thread" ("guest_user_id", "started_at");
   CREATE INDEX ON "conversation_thread" ("booking_id", "started_at");
   CREATE INDEX ON "conversation_message" ("conversation_id", "created_at");

   ALTER TABLE "conversation_thread"
     ADD FOREIGN KEY ("guest_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_thread"
     ADD FOREIGN KEY ("session_id") REFERENCES "session" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_thread"
     ADD FOREIGN KEY ("booking_id") REFERENCES "booking" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_thread"
     ADD FOREIGN KEY ("resort_id") REFERENCES "resort" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_message"
     ADD FOREIGN KEY ("conversation_id") REFERENCES "conversation_thread" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_message"
     ADD FOREIGN KEY ("sender_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_message"
     ADD FOREIGN KEY ("reply_to_message_id") REFERENCES "conversation_message" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_memory_snapshot"
     ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_memory_snapshot"
     ADD FOREIGN KEY ("booking_id") REFERENCES "booking" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_memory_snapshot"
     ADD FOREIGN KEY ("conversation_id") REFERENCES "conversation_thread" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_memory_snapshot"
     ADD FOREIGN KEY ("source_message_start_id") REFERENCES "conversation_message" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "conversation_memory_snapshot"
     ADD FOREIGN KEY ("source_message_end_id") REFERENCES "conversation_message" ("id") DEFERRABLE INITIALLY IMMEDIATE;

Why this is needed:

* the agent needs raw transcript storage in ``conversation_message``
* the system needs thread-level state in ``conversation_thread``
* the memory system needs compressed context in ``conversation_memory_snapshot``

5. Proposals And Confirmations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This model supports the propose-then-confirm flow described in the larger
architecture document.

.. code-block:: sql

   CREATE TYPE "proposal_actor_type" AS ENUM (
     'guest',
     'staff',
     'system'
   );

   CREATE TYPE "proposal_status" AS ENUM (
     'drafted',
     'presented',
     'confirmed',
     'rejected',
     'expired',
     'executed',
     'execution_failed'
   );

   CREATE TABLE "proposal_action" (
     "id" text PRIMARY KEY,
     "booking_id" text,
     "user_id" text,
     "created_by_actor_type" proposal_actor_type NOT NULL,
     "created_by_user_id" text,
     "confirmation_actor_type" proposal_actor_type NOT NULL,
     "status" proposal_status NOT NULL DEFAULT 'drafted',
     "tool_name" text NOT NULL,
     "action_summary" text NOT NULL,
     "risk_level" text NOT NULL,
     "arguments_json" jsonb NOT NULL,
     "confirmation_ui_json" jsonb,
     "result_json" jsonb,
     "error_text" text,
     "idempotency_key" text NOT NULL UNIQUE,
     "expires_at" timestamp NOT NULL,
     "presented_at" timestamp,
     "confirmed_at" timestamp,
     "executed_at" timestamp,
     "created_at" timestamp NOT NULL,
     "updated_at" timestamp NOT NULL
   );

   CREATE TABLE "proposal_decision_log" (
     "id" text PRIMARY KEY,
     "proposal_id" text NOT NULL,
     "actor_user_id" text,
     "decision" text NOT NULL,
     "note" text,
     "created_at" timestamp NOT NULL
   );

   ALTER TABLE "proposal_action"
     ADD FOREIGN KEY ("booking_id") REFERENCES "booking" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "proposal_action"
     ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "proposal_action"
     ADD FOREIGN KEY ("created_by_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "proposal_decision_log"
     ADD FOREIGN KEY ("proposal_id") REFERENCES "proposal_action" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "proposal_decision_log"
     ADD FOREIGN KEY ("actor_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

6. Escalations
^^^^^^^^^^^^^^
This model supports service recovery, manager intervention, and incident
tracking.

.. code-block:: sql

   CREATE TYPE "escalation_severity" AS ENUM (
     'low',
     'medium',
     'high',
     'critical'
   );

   CREATE TYPE "escalation_status" AS ENUM (
     'detected',
     'open',
     'acknowledged',
     'mitigation_in_progress',
     'resolved',
     'cancelled_false_positive'
   );

   CREATE TABLE "escalation_case" (
     "id" text PRIMARY KEY,
     "booking_id" text,
     "room_id" text,
     "service_request_id" text,
     "guest_user_id" text,
     "owner_staff_id" text,
     "severity" escalation_severity NOT NULL,
     "status" escalation_status NOT NULL DEFAULT 'detected',
     "summary" text NOT NULL,
     "sentiment_score" numeric(5,4),
     "trigger_message_id" text,
     "opened_at" timestamp NOT NULL,
     "acknowledged_at" timestamp,
     "resolved_at" timestamp,
     "resolution_summary" text,
     "created_at" timestamp NOT NULL,
     "updated_at" timestamp NOT NULL
   );

   CREATE TABLE "escalation_event" (
     "id" text PRIMARY KEY,
     "escalation_id" text NOT NULL,
     "actor_user_id" text,
     "event_type" text NOT NULL,
     "note" text,
     "payload_json" jsonb,
     "created_at" timestamp NOT NULL
   );

   ALTER TABLE "escalation_case"
     ADD FOREIGN KEY ("booking_id") REFERENCES "booking" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "escalation_case"
     ADD FOREIGN KEY ("room_id") REFERENCES "room" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "escalation_case"
     ADD FOREIGN KEY ("service_request_id") REFERENCES "service_request" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "escalation_case"
     ADD FOREIGN KEY ("guest_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "escalation_case"
     ADD FOREIGN KEY ("owner_staff_id") REFERENCES "internal_staff" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "escalation_case"
     ADD FOREIGN KEY ("trigger_message_id") REFERENCES "conversation_message" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "escalation_event"
     ADD FOREIGN KEY ("escalation_id") REFERENCES "escalation_case" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "escalation_event"
     ADD FOREIGN KEY ("actor_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

7. Check-In Verification
^^^^^^^^^^^^^^^^^^^^^^^^
This is the missing operational model for arrival validation now that the
project no longer uses access-code concepts.

.. code-block:: sql

   CREATE TYPE "check_in_verification_method" AS ENUM (
     'front_desk_manual',
     'document_check',
     'staff_override',
     'self_check_in'
   );

   CREATE TYPE "check_in_verification_status" AS ENUM (
     'pending',
     'verified',
     'rejected',
     'cancelled'
   );

   CREATE TABLE "check_in_verification" (
     "id" text PRIMARY KEY,
     "booking_id" text NOT NULL,
     "guest_user_id" text NOT NULL,
     "room_id" text NOT NULL,
     "verified_by_staff_id" text,
     "method" check_in_verification_method NOT NULL,
     "status" check_in_verification_status NOT NULL DEFAULT 'pending',
     "notes" text,
     "attempted_at" timestamp NOT NULL,
     "verified_at" timestamp,
     "created_at" timestamp NOT NULL
   );

   ALTER TABLE "check_in_verification"
     ADD FOREIGN KEY ("booking_id") REFERENCES "booking" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "check_in_verification"
     ADD FOREIGN KEY ("guest_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "check_in_verification"
     ADD FOREIGN KEY ("room_id") REFERENCES "room" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "check_in_verification"
     ADD FOREIGN KEY ("verified_by_staff_id") REFERENCES "internal_staff" ("id") DEFERRABLE INITIALLY IMMEDIATE;

8. Staff Shifts, Workload, And Assignment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The current schema can store who is assigned on a request, but not staff shift
presence, load, or assignment history. The following tables support queueing and
dispatch.

.. code-block:: sql

   CREATE TYPE "staff_shift_status" AS ENUM (
     'scheduled',
     'checked_in',
     'on_break',
     'checked_out',
     'cancelled'
   );

   CREATE TYPE "assignment_target_type" AS ENUM (
     'service_request',
     'service_booking',
     'room',
     'escalation'
   );

   CREATE TYPE "assignment_status" AS ENUM (
     'assigned',
     'accepted',
     'in_progress',
     'completed',
     'cancelled',
     'reassigned'
   );

   CREATE TABLE "staff_shift" (
     "id" text PRIMARY KEY,
     "staff_id" text NOT NULL,
     "resort_id" text NOT NULL,
     "shift_start" timestamp NOT NULL,
     "shift_end" timestamp NOT NULL,
     "status" staff_shift_status NOT NULL DEFAULT 'scheduled',
     "checked_in_at" timestamp,
     "checked_out_at" timestamp,
     "created_at" timestamp NOT NULL,
     "updated_at" timestamp NOT NULL
   );

   CREATE TABLE "staff_assignment" (
     "id" text PRIMARY KEY,
     "staff_id" text NOT NULL,
     "target_type" assignment_target_type NOT NULL,
     "target_id" text NOT NULL,
     "booking_id" text,
     "room_id" text,
     "status" assignment_status NOT NULL DEFAULT 'assigned',
     "priority_score" integer,
     "assigned_by_user_id" text,
     "assigned_at" timestamp NOT NULL,
     "accepted_at" timestamp,
     "completed_at" timestamp,
     "notes" text
   );

   CREATE INDEX ON "staff_shift" ("staff_id", "shift_start");
   CREATE INDEX ON "staff_assignment" ("staff_id", "status");
   CREATE INDEX ON "staff_assignment" ("target_type", "target_id");

   ALTER TABLE "staff_shift"
     ADD FOREIGN KEY ("staff_id") REFERENCES "internal_staff" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "staff_shift"
     ADD FOREIGN KEY ("resort_id") REFERENCES "resort" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "staff_assignment"
     ADD FOREIGN KEY ("staff_id") REFERENCES "internal_staff" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "staff_assignment"
     ADD FOREIGN KEY ("booking_id") REFERENCES "booking" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "staff_assignment"
     ADD FOREIGN KEY ("room_id") REFERENCES "room" ("id") DEFERRABLE INITIALLY IMMEDIATE;

   ALTER TABLE "staff_assignment"
     ADD FOREIGN KEY ("assigned_by_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

9. Service Request Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
For the agentic workflows in the concierge spec, ``service_request`` needs
priority, SLA, and richer lifecycle support.

.. code-block:: sql

   ALTER TYPE "service_request_status" ADD VALUE IF NOT EXISTS 'acknowledged';
   ALTER TYPE "service_request_status" ADD VALUE IF NOT EXISTS 'blocked';

   CREATE TYPE "service_request_priority" AS ENUM (
     'p1_immediate',
     'p2_time_sensitive',
     'p3_standard',
     'p4_deferred'
   );

   ALTER TABLE "service_request"
     ADD COLUMN "created_by_user_id" text,
     ADD COLUMN "priority" service_request_priority NOT NULL DEFAULT 'p3_standard',
     ADD COLUMN "requested_for_time" timestamp,
     ADD COLUMN "acknowledged_at" timestamp,
     ADD COLUMN "sla_due_at" timestamp,
     ADD COLUMN "resolution_note" text,
     ADD COLUMN "updated_at" timestamp NOT NULL DEFAULT now();

   ALTER TABLE "service_request"
     ADD FOREIGN KEY ("created_by_user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

Recommended rule:

* keep ``assigned_to`` for backward compatibility if needed
* move operational dispatch logic to ``staff_assignment`` over time

10. Notification Payload Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The current ``notification`` table is enough for delivery state but not for real
message rendering, retries, or correlation.

.. code-block:: sql

   CREATE TYPE "notification_priority" AS ENUM (
     'low',
     'normal',
     'high',
     'urgent'
   );

   ALTER TABLE "notification"
     ADD COLUMN "title" text,
     ADD COLUMN "body" text,
     ADD COLUMN "priority" notification_priority NOT NULL DEFAULT 'normal',
     ADD COLUMN "template_key" text,
     ADD COLUMN "payload_json" jsonb,
     ADD COLUMN "correlation_key" text,
     ADD COLUMN "retry_count" integer NOT NULL DEFAULT 0,
     ADD COLUMN "updated_at" timestamp NOT NULL DEFAULT now();

11. Idempotency Records
^^^^^^^^^^^^^^^^^^^^^^^
This table prevents duplicate writes when the frontend retries or the agent
replays a proposal confirmation.

.. code-block:: sql

   CREATE TABLE "idempotency_record" (
     "id" text PRIMARY KEY,
     "scope" text NOT NULL,
     "idempotency_key" text NOT NULL UNIQUE,
     "request_hash" text NOT NULL,
     "request_body_json" jsonb,
     "response_status_code" integer,
     "response_body_json" jsonb,
     "resource_type" text,
     "resource_id" text,
     "created_at" timestamp NOT NULL,
     "expires_at" timestamp NOT NULL
   );

Recommended Backend Summary
^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the backend team wants the leanest viable extension set, the highest-value
tables to add first are:

* ``internal_staff``
* ``conversation_thread``
* ``conversation_message``
* ``guest_preference_signal``
* ``proposal_action``
* ``check_in_verification``

The next wave after that should be:

* ``conversation_memory_snapshot``
* ``escalation_case``
* ``staff_shift``
* ``staff_assignment``
* ``idempotency_record``

Contract Design Principles
--------------------------
The team should use these rules while designing the contracts:

1. The backend owns canonical business state.
2. The frontend talks only to the backend public API.
3. The agent is a private service behind the backend.
4. The agent can read backend-owned internal tool APIs.
5. The agent should return proposed write actions, not silently execute
   canonical business writes.
6. Every write path must define confirmation, authorization, audit behavior,
   and idempotency.
7. Contract names should follow domain language already present in the schema
   where possible.

Implementation Plan
-------------------
The team should execute contract design in five workstreams.

Workstream 1: Canonical Domain Model Freeze
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Objective:
  Turn the SQL schema into a shared contract vocabulary that frontend, backend,
  and agent teams all use.

Tasks:

* freeze canonical names for room, booking, service booking, service
  request, and notification resources
* normalize enum casing between database values and API values
* define which database fields are public, internal, or backend-only
* document required foreign-key context for each major resource
* define canonical identifiers for ``user_id``, ``booking_id``, ``room_id``,
  ``service_request_id``, and ``notification_id``

Deliverables:

* domain glossary
* enum mapping sheet
* resource shape sheet

Workstream 2: Public Backend API Contracts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Objective:
  Define the frontend-to-backend contracts for the MVP domains already backed by
  schema.

Phase 1 contract surface:

* authentication endpoints
* room availability and room detail endpoints
* booking create, get, cancel, and check-in or checkout support endpoints
* service catalog and service booking endpoints
* service request create, list, and status endpoints
* notification list or status endpoints

Tasks:

* define request and response bodies for each public endpoint
* define pagination, filtering, and sorting rules where needed
* define standard error responses and validation failures
* define auth requirements per endpoint
* define which endpoints are guest-only, staff-only, or admin-only

Deliverables:

* public OpenAPI draft
* role-to-endpoint matrix
* standard error schema

Workstream 3: Backend-To-Agent Private Contracts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Objective:
  Define how the backend asks the agent to reason, classify, rank, and draft
  proposals.

Initial private endpoints:

* ``POST /internal/agent/respond``
* ``POST /internal/agent/recommend``
* ``POST /internal/agent/sentiment/score``
* ``POST /internal/agent/memory/summarize``

Tasks:

* map the canonical intent envelope from the specification onto backend request
  payloads
* define agent response shapes for plain answers, tool-read results, and
  proposed write actions
* define confidence, routing, and fallback fields
* define the agent error contract for timeout, low-confidence, and unavailable
  tool scenarios

Deliverables:

* private agent API spec
* intent envelope schema
* agent response union schema

Workstream 4: Agent Tool Contracts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Objective:
  Define the internal contracts the agent uses to read backend state and propose
  actions.

Start with schema-backed read tools:

* ``get_current_stay_context``
* ``search_room_inventory``
* ``get_booking_record``
* ``get_room_status_snapshot``
* ``get_service_catalog``
* ``get_guest_service_history`` using booking-linked service requests
* ``get_notification_history`` if the backend wants the agent to explain
  delivery state

Start with schema-backed write proposals:

* ``create_booking``
* ``cancel_booking``
* ``create_service_booking``
* ``create_service_request``
* ``update_service_request_status``
* ``update_room_status``

Tasks:

* define one shared tool envelope for reads and writes
* define proposal payloads for all write tools
* attach idempotency requirements to every write proposal
* attach audit fields to every tool execution
* clearly mark which tool contracts are ready now versus blocked by missing
  schema support

Deliverables:

* internal tool catalog v1
* proposal payload schema
* tool permission matrix

Workstream 5: Realtime, Events, And Schema Gap Backlog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Objective:
  Define the live update contracts and isolate the schema changes needed for the
  larger concierge vision.

Tasks:

* define SSE or WebSocket event shapes for guest chat responses, staff queue
  updates, room-state changes, and request-status changes
* define notification event payloads beyond the current enum-only model
* define the schema backlog for roles, proposals, escalations, memory,
  check-in validation events, and chat transcripts
* separate ``must-have for MVP contracts`` from ``future-ready extension``

Deliverables:

* event contract sheet
* schema extension backlog
* MVP versus future-ready boundary note

Recommended Task Order
----------------------
The team should not try to design every contract at once. The most efficient
sequence is:

1. Freeze canonical enums and resource names from the SQL.
2. Draft public backend contracts for bookings, rooms, service requests,
   and notifications.
3. Draft the private backend-to-agent request and response contracts.
4. Draft the internal tool envelopes and proposal format.
5. Draft realtime event contracts.
6. Convert missing capabilities into explicit backend backlog items.

Immediate Starter Tasks
-----------------------
These are the first tasks the team can start immediately without waiting for new
schema files.

Task A: Build the canonical resource map
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* map each SQL table to one API resource or internal-only entity
* decide which table names stay internal and which become public API names
* freeze enum naming conventions

Task B: Draft MVP endpoint inventory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* turn ``user``, ``room``, ``booking``, ``service_booking``,
  ``service_request``, and ``notification`` into first-pass endpoints
* define guest-facing versus staff-facing variants
* list fields returned in summary views versus detail views

Task C: Draft proposal contract v1
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* define a proposal schema even before a proposal table exists
* specify ``proposal_id``, ``action_summary``, ``actor_role``, ``expires_at``,
  ``idempotency_key``, ``impacted_entities``, and ``confirmation_ui``
* mark this as requiring backend persistence design

Task D: Draft private agent request contract
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* package guest message, active booking context, channel, and auth context
  into one backend-to-agent payload
* define the allowed agent outputs: direct answer, read-tool plan, or write
  proposal

Task E: Create schema gap issues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* roles and RBAC model
* proposal persistence model
* escalation model
* guest preference and memory model
* chat transcript or conversation model
* check-in verification model
* staff workload or assignment model

What We Still Need From Backend
-------------------------------
The schema is enough to start contract design, but we still need a few decisions
from the backend engineer before contracts can be considered final.

Required backend confirmations:

* API style preference: REST-only, REST plus SSE, or REST plus WebSocket
* official role model: guest, staff, admin, manager, housekeeping, maintenance
* confirmation model: where proposal data will be stored and how TTL is handled
* state-transition rules for room and booking changes
* whether service bookings and service requests are both exposed publicly or one
  remains internal
* whether notifications are queryable by guests, staff, or both
* how check-in validation should be represented in API contracts and persistence

Recommended First Meeting Agenda With Backend
---------------------------------------------
Use the first backend alignment meeting to lock only the decisions that shape
contracts.

Agenda:

* confirm the SQL as the contract-design source of truth for current backend
* confirm canonical role model
* confirm which resources are public API resources
* confirm write actions that require propose-then-confirm
* confirm realtime transport choice
* confirm the first schema extension batch needed for agentic features

Definition Of Ready For Contract Drafting
-----------------------------------------
Contract drafting can begin immediately if the team accepts these assumptions:

* the SQL schema is the current backend baseline
* bookings, rooms, service bookings, service requests, and notifications
  are the MVP resource set
* agent-specific persistence such as proposals, escalations, and memory will be
  tracked as schema backlog items until approved

If those assumptions hold, the team does not need to wait for more backend
artifacts before starting the first contract draft.

Recommended Next Deliverables
-----------------------------
After this plan, the next concrete artifacts should be:

1. ``public_api_contract_v1`` for frontend-to-backend endpoints
2. ``agent_private_contract_v1`` for backend-to-agent calls
3. ``tool_contract_catalog_v1`` for agent-to-backend internal tool APIs
4. ``schema_gap_backlog_v1`` for missing tables and enums
