Backend And Frontend Integration Plan
=====================================

Purpose
-------
This document defines how to integrate the current agent service
with the backend and how to expose it cleanly through the frontend.

This plan is based on the current live agent implementation in this
repository, not on a future idealized architecture.

Integration Principle
---------------------
The backend should be the orchestrator and source of truth.

Recommended responsibility split:

* frontend owns chat presentation and user interaction
* backend owns authentication, persistence, execution, and notifications
* agent service owns interpretation, dialogue continuity, planning, and
  proposal generation

The frontend should not call the agent directly.
The agent should not be treated as the source of truth for reservation or
service state.

Target Runtime Flow
-------------------
The recommended production flow is:

1. frontend sends a guest message to the backend
2. backend loads thread and booking context from its own database
3. backend calls ``POST /internal/agent/respond``
4. agent returns:

   * assistant message
   * optional proposals
   * optional handover
   * routing and intent metadata

5. backend decides whether to execute the proposal
6. backend performs the real write in backend-owned domain services
7. backend stores:

   * guest message
   * agent response
   * proposal execution result
   * updated booking or service state

8. backend returns a frontend-friendly response

Current Agent Endpoints
-----------------------
The current agent service exposes:

* ``GET /health``
* ``POST /internal/agent/respond``
* ``POST /internal/agent/recommend``
* ``POST /internal/agent/sentiment/score``
* ``POST /internal/agent/memory/summarize``

The main integration endpoint is ``POST /internal/agent/respond``.

Backend To Agent Schema
-----------------------
The backend should call the agent with the current request contract.

Primary Endpoint
^^^^^^^^^^^^^^^^

``POST /internal/agent/respond``

Request schema:

.. code-block:: json

   {
     "request_id": "chat_req_001",
     "trace_id": "trace_001",
     "actor": {
       "actor_type": "guest",
       "user_id": "user_123",
       "internal_staff_id": null
     },
     "conversation": {
       "conversation_id": "thread_123",
       "channel": "web_chat",
       "language": "en"
     },
     "booking_context": {
       "booking_id": "reservation_123",
       "room_id": "room_201",
       "resort_id": "resort_1",
       "status": "pending"
     },
     "message": {
       "message_id": "msg_001",
       "content": "I want to book a room for tomorrow",
       "role": "user"
     },
     "policy_context": {
       "proposal_required_for_writes": true,
       "allowed_tool_names": [
         "create_booking",
         "create_service_booking",
         "create_service_request",
         "validate_guest_check_in"
       ]
     }
   }

Required request mapping rules:

* ``conversation.conversation_id`` must stay stable across turns in the same
  thread
* ``booking_context`` should be filled from backend truth when known
* ``booking_context.status`` must reflect real backend status such as
  ``pending``, ``confirmed``, or ``checked_in``
* ``policy_context.allowed_tool_names`` should be explicitly controlled by
  backend policy

Respond Response Schema
^^^^^^^^^^^^^^^^^^^^^^^

The current agent responds like this:

.. code-block:: json

   {
     "request_id": "chat_req_001",
     "response_type": "assistant_message_with_proposals",
     "intent": {
       "primary": "booking_search",
       "secondary": ["booking_create"],
       "confidence": 0.84
     },
     "assistant_message": {
       "role": "assistant",
       "content": "I found 3 available room option(s). Top matches: room 301 - suite - USD 450.00 per night - up to 4 guests, room 201 - deluxe - USD 320.00 per night - up to 3 guests, room 100 - standard - USD 250.00 per night - up to 3 guests. Please tell me the room number or room ID you prefer."
     },
     "proposals": [
       {
         "tool_name": "create_booking",
         "action_summary": "Book deluxe room from 2026-12-05 to 2026-12-07",
         "risk_level": "medium_transactional",
         "arguments": {
           "room_id": "room_201",
           "resort_id": "resort_1",
           "check_in_date": "2026-12-05",
           "check_out_date": "2026-12-07",
           "adults": 2,
           "children": 1,
           "special_requests": "Selected add-on service: Deep Tissue Massage"
         },
         "idempotency_key": "booking:room_201:2026-12-05:2026-12-07"
       }
     ],
     "handover": null,
     "routing": {
       "primary_agent": "BookingAgent",
       "confidence": 0.84
     },
     "errors": []
   }

Current response handling rules:

* ``response_type=assistant_message`` means no write proposal is present
* ``response_type=assistant_message_with_proposals`` means backend should
  inspect and possibly execute proposals
* ``response_type=clarification_required`` means frontend should display the
  assistant message as the next prompt
* ``response_type=handover_required`` means backend should route to staff or
  support handling

Supported Proposal Names
------------------------
The backend should initially support these proposal names:

* ``create_booking``
* ``create_service_booking``
* ``create_service_request``
* ``validate_guest_check_in``

Recommended backend executor table:

.. list-table::
   :header-rows: 1

   * - Proposal
     - Backend action
     - Notes
   * - ``create_booking``
     - create reservation
     - backend owns final reservation status and total
   * - ``create_service_booking``
     - create service booking
     - backend should enforce booking status rules
   * - ``create_service_request``
     - create operational service request
     - examples: towels, maintenance, laundry
   * - ``validate_guest_check_in``
     - perform staff-assisted check-in validation
     - should be restricted by actor and backend policy

Recommended Backend Chat Schema
-------------------------------
The frontend should call a backend endpoint such as
``POST /api/chat/messages``.

Recommended request schema:

.. code-block:: json

   {
     "threadId": "thread_123",
     "message": {
       "id": "msg_001",
       "content": "I want to book a room for tomorrow"
     },
     "bookingContext": {
       "bookingId": null,
       "roomId": null,
       "resortId": "resort_1"
     }
   }

Recommended backend response schema to frontend:

.. code-block:: json

   {
     "threadId": "thread_123",
     "message": {
       "id": "agent_msg_001",
       "role": "assistant",
       "content": "Before I check rooms, how many adults and children will be staying?"
     },
     "ui": {
       "kind": "text",
       "cards": []
     },
     "bookingContext": {
       "bookingId": null,
       "roomId": null,
       "resortId": "resort_1",
       "status": null
     },
     "agent": {
       "intent": {
         "primary": "booking_search",
         "secondary": ["booking_create"],
         "confidence": 0.84
       },
       "routing": {
         "primaryAgent": "BookingAgent",
         "confidence": 0.84
       },
       "responseType": "clarification_required",
       "handover": null,
       "errors": []
     },
     "execution": {
       "executed": false,
       "proposal": null,
       "result": null
     }
   }

Recommended frontend-friendly ``ui.kind`` values:

* ``text``
* ``clarification``
* ``room_options``
* ``booking_confirmation``
* ``service_catalog``
* ``service_request_confirmation``
* ``handover``

Recommended Frontend Card Schemas
---------------------------------
The frontend should not render raw proposal JSON by default.

Room options card:

.. code-block:: json

   {
     "kind": "room_options",
     "items": [
       {
         "roomId": "room_301",
         "roomNumber": "301",
         "roomType": "suite",
         "nightlyPriceCents": 45000,
         "nightlyPriceText": "USD 450.00",
         "maxGuests": 4,
         "bedConfiguration": "1 King",
         "notes": "Lake view"
       }
     ]
   }

Booking confirmation card:

.. code-block:: json

   {
     "kind": "booking_confirmation",
     "bookingId": "reservation_123",
     "status": "pending",
     "totalPriceCents": 64000,
     "totalPriceText": "USD 640.00",
     "serviceMessage": "Deep Tissue Massage has not been booked yet. I saved it in the reservation request, and it can be added once the booking is confirmed."
   }

Service catalog card:

.. code-block:: json

   {
     "kind": "service_catalog",
     "items": [
       {
         "serviceId": "svc_spa",
         "name": "Deep Tissue Massage",
         "category": "spa",
         "priceCents": 15000,
         "priceText": "USD 150.00",
         "durationMins": 60,
         "available": true
       }
     ]
   }

Service request confirmation card:

.. code-block:: json

   {
     "kind": "service_request_confirmation",
     "requestType": "housekeeping",
     "status": "submitted",
     "description": "Please send extra towels"
   }

Backend Integration Checklist
-----------------------------
The backend team should complete these items:

1. Create a backend chat endpoint such as ``POST /api/chat/messages``.
2. Persist a stable ``conversation_id`` or ``threadId`` for every guest chat.
3. Load current backend booking context before every agent call.
4. Map backend state into the agent ``booking_context`` fields:

   * ``booking_id``
   * ``room_id``
   * ``resort_id``
   * ``status``

5. Call ``POST /internal/agent/respond`` with the current message and context.
6. Parse ``response_type``, ``assistant_message``, ``proposals``, ``handover``,
   and ``errors``.
7. Implement a proposal executor map for:

   * ``create_booking``
   * ``create_service_booking``
   * ``create_service_request``
   * ``validate_guest_check_in``

8. Persist proposal execution results in backend-owned chat history.
9. Return frontend-friendly response objects and cards.
10. Let backend own notification or email sending after execution.

Frontend Integration Checklist
------------------------------
The frontend team should complete these items:

1. Build a single chat screen that talks only to the backend.
2. Render assistant messages and clarification prompts from backend response.
3. Render structured cards for:

   * room options
   * booking confirmation
   * service catalog
   * service request confirmation

4. Preserve the current ``threadId`` across the chat session.
5. Send typed user selections naturally, for example:

   * ``room 201``
   * ``add Deep Tissue Massage``
   * ``check my booking``

6. Show booking status using backend truth, not guessed frontend state.
7. Display handover state cleanly when backend returns a handoff decision.
8. Do not expose raw proposal JSON unless a debug mode is enabled.

Recommended Demo Scope
----------------------
To showcase the current system, the frontend should focus on these three
stories:

1. New reservation

   * hello
   * branch selection
   * dates
   * guest count
   * room selection
   * optional add-on selection
   * booking created

2. Existing booking support

   * check my booking
   * is my room ready
   * can I check in now

3. In-stay operational request

   * please send extra towels
   * the AC is not working

Known Current Integration Boundaries
------------------------------------
These are important current limits in the live implementation:

* the agent can draft and support ``create_service_booking``, but the backend
  may reject service-booking writes while reservation status is ``pending``
* reservation totals and status remain backend-authoritative
* notification and email sending appear backend-owned rather than agent-owned
* the agent supports multi-turn reasoning, but backend still must persist the
  real conversation and execution history

Recommended Delivery Order
--------------------------
Deliver the integration in this order:

1. backend chat endpoint
2. backend to agent request mapper
3. backend proposal execution map
4. frontend chat screen
5. frontend structured room and booking cards
6. existing booking lookup and check-in readiness flow
7. in-stay service request flow

Success Criteria
----------------
The integration is ready for demo when:

* a guest can complete a booking flow from frontend through backend to agent
* backend returns real booking ID and real booking status to frontend
* frontend can show booking lookup and check-in readiness from live backend data
* frontend can submit at least one operational service request
* handover and backend errors are rendered clearly instead of appearing as raw
  internal failures
