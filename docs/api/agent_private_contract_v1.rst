Agent Private Contract V1
=========================

Purpose
-------
This document defines the private contract between the backend and the agent
service. It is not a frontend contract. Only trusted backend services should be
allowed to call these endpoints.

The goal of the private contract is to let the backend outsource reasoning while
keeping business authority, state mutation, confirmation handling, and audit
ownership in the backend.

Private Contract Rules
----------------------

* the backend sends authenticated internal requests to the agent service
* the agent service never becomes the source of truth for bookings, rooms,
  service requests, or notifications
* the agent may read backend-owned internal tools
* the agent returns proposals for writes; it does not silently finalize
  canonical business mutations

Common Envelope
---------------
All private calls should include correlation and actor context.

Common Request Fields
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "request_id": "req_123",
     "trace_id": "trace_123",
     "actor": {
       "actor_type": "guest",
       "user_id": "user_1",
       "internal_staff_id": null
     },
     "conversation": {
       "conversation_id": "conv_001",
       "channel": "mobile_chat",
       "language": "en"
     },
     "booking_context": {
       "booking_id": "booking_123",
       "room_id": "room_101",
       "resort_id": "resort_1",
       "status": "checked_in"
     }
   }

Common Response Fields
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "request_id": "req_123",
     "routing": {
       "primary_agent": "ServiceRequestAgent",
       "confidence": 0.94
     },
     "errors": []
   }

Endpoint Inventory
------------------

``POST /internal/agent/respond``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use this for the main conversational runtime.

Request:

.. code-block:: json

   {
     "request_id": "req_123",
     "trace_id": "trace_123",
     "actor": {
       "actor_type": "guest",
       "user_id": "user_1",
       "internal_staff_id": null
     },
     "conversation": {
       "conversation_id": "conv_001",
       "channel": "mobile_chat",
       "language": "en"
     },
     "booking_context": {
       "booking_id": "booking_123",
       "room_id": "room_101",
       "resort_id": "resort_1",
       "status": "checked_in"
     },
     "message": {
       "message_id": "msg_009",
       "content": "I need two extra towels."
     },
     "policy_context": {
       "proposal_required_for_writes": true,
       "allowed_tool_names": [
         "get_current_stay_context",
         "get_service_catalog",
         "create_service_request"
       ]
     }
   }

Response:

.. code-block:: json

   {
     "request_id": "req_123",
     "response_type": "assistant_message_with_proposals",
     "intent": {
       "primary": "service_request",
       "secondary": ["housekeeping_request"],
       "confidence": 0.94
     },
     "assistant_message": {
       "role": "assistant",
       "content": "I can request two extra towels for your room."
     },
     "proposals": [
       {
         "tool_name": "create_service_request",
         "action_summary": "Create housekeeping request for two extra towels",
         "risk_level": "low_operational",
         "arguments": {
           "booking_id": "booking_123",
           "type": "housekeeping",
           "description": "Need two extra towels"
         },
         "idempotency_key": "service_request_res_123_towels_1"
       }
     ],
     "handover": null,
     "routing": {
       "primary_agent": "ServiceRequestAgent",
       "confidence": 0.94
     },
     "errors": []
   }

Allowed response types:

* ``assistant_message``
* ``assistant_message_with_proposals``
* ``handover_required``
* ``clarification_required``

``POST /internal/agent/recommend``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use this for proactive or user-initiated recommendation flows.

Request:

.. code-block:: json

   {
     "request_id": "req_200",
     "trace_id": "trace_200",
     "actor": {
       "actor_type": "guest",
       "user_id": "user_1",
       "internal_staff_id": null
     },
     "booking_context": {
       "booking_id": "booking_123",
       "resort_id": "resort_1",
       "status": "checked_in"
     },
     "recommendation_scope": {
       "category": "dining",
       "time_window": "tonight",
       "max_results": 3
     }
   }

Response:

.. code-block:: json

   {
     "request_id": "req_200",
     "recommendations": [
       {
         "id": "rec_1",
         "category": "dining",
         "title": "Quiet dinner at the rooftop restaurant",
         "reason": "Matches the guest's preference for calm evening settings.",
         "confidence": 0.89
       }
     ],
     "proposals": [],
     "errors": []
   }

``POST /internal/agent/sentiment/score``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use this for service risk detection and escalation triggers.

Request:

.. code-block:: json

   {
     "request_id": "req_300",
     "trace_id": "trace_300",
     "conversation_id": "conv_001",
     "message": {
       "message_id": "msg_011",
       "content": "The room is too hot and nobody is helping."
     }
   }

Response:

.. code-block:: json

   {
     "request_id": "req_300",
     "sentiment": {
       "label": "negative",
       "score": -0.82
     },
     "risk": {
       "severity": "high",
       "handover_required": true
     },
     "errors": []
   }

``POST /internal/agent/memory/summarize``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use this for promoting message history into stay memory or durable preference
signals.

Request:

.. code-block:: json

   {
     "request_id": "req_400",
     "trace_id": "trace_400",
     "conversation_id": "conv_001",
     "booking_id": "booking_123",
     "user_id": "user_1",
     "message_ids": ["msg_001", "msg_002", "msg_003"]
   }

Response:

.. code-block:: json

   {
     "request_id": "req_400",
     "snapshot": {
       "scope": "stay",
       "summary_text": "Guest prefers quiet evenings and late housekeeping.",
       "structured_memory_json": {
         "timing_pattern": "late_morning_housekeeping",
         "preference": "quiet_dining"
       },
       "confidence": 0.88
     },
     "candidate_signals": [
       {
         "signal_type": "preference",
         "key": "quiet_dining",
         "value_text": "quiet dining atmosphere",
         "confidence": 0.86
       }
     ],
     "errors": []
   }

Response Contracts
------------------
The backend should treat the following agent outputs as authoritative only in
their reasoning domain:

* intent classification
* recommendation ranking
* sentiment scoring
* memory candidates
* proposal drafts

The backend should remain authoritative for:

* authorization
* state transitions
* proposal persistence
* confirmation handling
* final write execution

Error Contract
--------------
Private agent errors should use stable codes so the backend can degrade
gracefully.

.. code-block:: json

   {
     "request_id": "req_500",
     "errors": [
       {
         "code": "tool_unavailable",
         "message": "Required internal tool was unavailable.",
         "details": {
           "tool_name": "get_current_stay_context"
         }
       }
     ]
   }

Recommended error codes:

* ``tool_unavailable``
* ``low_confidence``
* ``timeout``
* ``policy_context_missing``
* ``booking_context_missing``

Open Decisions
--------------

* ``Tool Invocation Model``
  The agent service will ``not call tools directly during `respond```. Instead, it will ``return a structured read plan``, and the ``backend will be responsible for executing it``.
  → *Agent decides, backend executes.*  

* ``Recommendation Ranking Ownership``  
  ``All recommendation ranking logic remains within the agent service.``
  The backend may provide supporting scoring utilities, but ``final ranking decisions are owned by the agent``.

* ``Memory Summarization Strategy``
  Memory summarization will be handled **asynchronously via a queue-backed job**, rather than running synchronously in the request path.