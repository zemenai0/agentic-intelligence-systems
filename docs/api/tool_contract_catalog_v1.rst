Tool Contract Catalog V1
========================

Purpose
-------
This document defines the internal tool contract between the agent service and
the backend. These tools are not public APIs. They are internal capabilities the
agent uses to read trusted state and propose business actions.

Transport Rule
--------------
The logical contract is tool-based. The recommended HTTP transport is:

* ``POST /internal/tools/{tool_name}``

The backend may implement the same contract through internal service calls as
long as the request and response shapes remain stable.

Shared Tool Envelope
--------------------

Request
^^^^^^^

.. code-block:: json

   {
     "request_id": "req_123",
     "tool_name": "get_current_stay_context",
     "tool_type": "READ",
     "actor": {
       "actor_type": "guest",
       "user_id": "user_1",
       "internal_staff_id": null
     },
     "reason": "Need active stay context before drafting a service request.",
     "arguments": {
       "booking_id": "booking_123"
     }
   }

Response
^^^^^^^^

.. code-block:: json

   {
     "request_id": "req_123",
     "tool_name": "get_current_stay_context",
     "ok": true,
     "result": {},
     "error": null,
     "audit": {
       "tool_name": "get_current_stay_context",
       "executed_at": "2026-04-10T18:12:00Z"
     }
   }

READ Tools
----------
READ tools execute immediately and never mutate canonical state.

``get_current_stay_context``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id`` or ``user_id``

Result:

.. code-block:: json

   {
     "booking_id": "booking_123",
     "guest_user_id": "user_1",
     "room": {
       "id": "room_101",
       "room_number": "101",
       "status": "occupied"
     },
     "stay_status": "checked_in",
     "open_service_requests": [
       {
         "id": "sr_101",
         "type": "housekeeping",
         "status": "open"
       }
     ]
   }

``search_room_inventory``
^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``check_in_date``
* ``check_out_date``
* ``adults``
* ``children``
* ``room_type`` optional
* ``accessible`` optional

Result:

* array of room summaries with rate context and availability flag

``get_booking_record``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id``

Result:

* booking detail including room summary and current status

``get_check_in_readiness``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id``

Result:

.. code-block:: json

   {
     "booking_id": "booking_123",
     "status": "eligible",
     "reason": "Booking is confirmed and room is ready."
   }

``get_room_status_snapshot``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``room_id``

Result:

* room state, previous transition summary, and any maintenance lock indicators

``get_service_catalog``
^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``resort_id`` optional
* ``category_slug`` optional

Result:

* service list with category, price, duration, and availability

``get_guest_service_history``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``user_id`` or ``booking_id``
* ``limit`` optional

Result:

* list of service bookings and service requests in actor scope

``get_notification_history``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``user_id``
* ``limit`` optional

Result:

* recent notifications with event, channel, status, and timestamps

WRITE Proposal Tools
--------------------
WRITE tools are never silently finalized by the agent. The tool contract exists
so the backend can validate arguments, create proposals, and later execute the
confirmed action.

``create_booking``
^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``room_id``
* ``check_in_date``
* ``check_out_date``
* ``adults``
* ``children``
* ``special_requests`` optional

Proposal result:

.. code-block:: json

   {
     "proposal_type": "booking_create",
     "action_summary": "Reserve Room 101 from 2026-04-10 to 2026-04-13",
     "risk_level": "medium_transactional",
     "idempotency_key": "booking_room_101_2026-04-10_2026-04-13"
   }

``cancel_booking``
^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id``
* ``reason`` optional

Proposal result:

* cancellation summary plus policy hints

``create_service_booking``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id``
* ``service_id``
* ``scheduled_at`` optional
* ``quantity``
* ``notes`` optional

Proposal result:

* service booking summary and quoted total

``create_service_request``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id``
* ``type``
* ``description``
* ``requested_for_time`` optional

Proposal result:

* service request summary with default priority

``update_service_request_status``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``service_request_id``
* ``new_status``
* ``resolution_note`` optional

Proposal result:

* status-transition summary and conflict checks

``update_room_status``
^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``room_id``
* ``new_status``
* ``reason``

Proposal result:

* room-state transition summary

``validate_guest_check_in``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id``
* ``verification_source``
* ``verified_by_staff_id`` optional

Proposal result:

* check-in validation summary and occupancy transition preview

``register_guest_checkout``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arguments:

* ``booking_id``
* ``checkout_source``

Proposal result:

* checkout summary plus room-turnover trigger preview

Permission Matrix
-----------------

* guest actor may request ``create_booking``, ``cancel_booking``,
  ``create_service_booking``, ``create_service_request``, and
  ``register_guest_checkout``
* staff actor may request ``update_service_request_status``,
  ``update_room_status``, ``validate_guest_check_in``, and
  ``register_guest_checkout``
* manager or admin actor may approve escalation-linked or policy-sensitive
  proposals

Idempotency Rules
-----------------

* every WRITE proposal must include an ``idempotency_key``
* the same confirmed proposal must not create duplicate bookings, service
  requests, or room transitions
* duplicate confirm requests should return the previously executed result

Audit Rules
-----------

Every tool execution should emit:

* ``tool_name``
* ``actor_type``
* ``actor_user_id`` or ``internal_staff_id``
* ``reason``
* ``executed_at``
* ``proposal_id`` when applicable
* sanitized outcome

Open Decisions
--------------

* whether the backend wants one generic ``/internal/tools/{tool_name}`` route or
  domain-specific internal routes - domain-specific internal routes.
* whether service history should merge ``service_booking`` and
  ``service_request`` in one tool result or remain split - keep split for clarity.
* whether room-status writes should always route through proposal flow or allow
  direct staff execution for low-risk transitions - Hybrid room status → optimize for staff efficiency without sacrificing control
