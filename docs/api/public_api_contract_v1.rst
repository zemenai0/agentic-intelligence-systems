Public API Contract V1
======================

Purpose
-------
This document defines the first public API contract between HabitaLife clients
and the backend. It is the contract that guest-facing frontends and staff
dashboards should implement against.

This contract assumes:

* the backend is the only public entrypoint
* the backend owns canonical business state
* the agent service is private and not directly reachable from clients
* session-based authentication is used instead of JWT-style access tokens

Contract Conventions
--------------------
The v1 public API should follow these conventions unless the backend team has a
stronger existing standard.

Authentication
^^^^^^^^^^^^^^

* clients authenticate through the auth endpoints and establish an authenticated
  session
* the public contract assumes session-based auth and should not expose JWT
  semantics to frontend teams
* guest permissions are derived from the authenticated ``user``
* staff permissions are derived from ``internal_staff`` plus related role rules

Identifiers And Timestamps
^^^^^^^^^^^^^^^^^^^^^^^^^^

* all resource IDs are opaque strings
* timestamps are ISO-8601 UTC strings
* dates are ``YYYY-MM-DD``
* currency amounts are integer minor units such as ``price_cents``

Success Shape
^^^^^^^^^^^^^

.. code-block:: json

   {
     "data": {},
     "meta": {
       "request_id": "req_123"
     }
   }

Error Shape
^^^^^^^^^^^

.. code-block:: json

   {
     "error": {
       "code": "booking_not_found",
       "message": "Booking was not found for this guest.",
       "details": {},
       "request_id": "req_123"
     }
   }

Pagination Shape
^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "data": [],
     "meta": {
       "request_id": "req_123",
       "page": 1,
       "page_size": 20,
       "total": 87
     }
   }

Core Resource Shapes
--------------------
These are the core public resource shapes that other endpoint contracts should
reuse.

Room Summary
^^^^^^^^^^^^

.. code-block:: json

   {
     "id": "room_101",
     "resort_id": "resort_1",
     "room_number": "101",
     "type": "deluxe",
     "floor": 1,
     "size_sqm": 38.5,
     "max_guests": 2,
     "bed_configuration": "1 king bed",
     "status": "available",
     "base_price_cents": 18000,
     "accessible": false,
     "amenities": [
       {
         "id": "amenity_wifi",
         "name": "WiFi",
         "category": "technology",
         "icon_slug": "wifi"
       }
     ],
     "images": [
       {
         "id": "img_1",
         "url": "https://example.com/room-101.jpg",
         "caption": "Mountain view",
         "sort_order": 0
       }
     ]
   }

Booking Detail
^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "id": "booking_123",
     "user_id": "user_1",
     "room_id": "room_101",
     "resort_id": "resort_1",
     "check_in_date": "2026-04-10",
     "check_out_date": "2026-04-13",
     "adults": 2,
     "children": 1,
     "status": "confirmed",
     "total_price_cents": 54000,
     "special_requests": "Quiet room if possible",
     "created_at": "2026-04-03T09:00:00Z",
     "updated_at": "2026-04-03T09:00:00Z",
     "room": {
       "id": "room_101",
       "room_number": "101",
       "type": "deluxe",
       "status": "booked"
     },
     "check_in_readiness": {
       "status": "eligible",
       "reason": "Booking is confirmed and room is ready."
     }
   }

Service Request Detail
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "id": "sr_101",
     "booking_id": "booking_123",
     "assigned_to": "staff_42",
     "type": "housekeeping",
     "description": "Need two extra towels",
     "status": "open",
     "priority": "p3_standard",
     "requested_at": "2026-04-10T18:12:00Z",
     "acknowledged_at": null,
     "resolved_at": null,
     "resolution_note": null
   }

Proposal Action Detail
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "id": "prop_001",
     "tool_name": "create_service_request",
     "action_summary": "Create housekeeping request for two extra towels",
     "risk_level": "low_operational",
     "status": "presented",
     "expires_at": "2026-04-10T18:30:00Z",
     "confirmation_ui": {
       "title": "Confirm request",
       "body": "We will notify staff and track progress for you.",
       "confirm_label": "Confirm",
       "cancel_label": "Cancel"
     },
     "impacted_entities": {
       "booking_id": "booking_123",
       "room_id": "room_101"
     }
   }

Chat Response Detail
^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "conversation_id": "conv_001",
     "message_id": "msg_010",
     "assistant_message": {
       "role": "assistant",
       "content": "I can request two extra towels for your room."
     },
     "proposals": [
       {
         "id": "prop_001",
         "tool_name": "create_service_request",
         "action_summary": "Create housekeeping request for two extra towels",
         "status": "presented",
         "expires_at": "2026-04-10T18:30:00Z"
       }
     ],
     "handover": null
   }

Public Endpoint Inventory
-------------------------
The following endpoints are the recommended v1 public contract surface.

Authentication
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``POST``
     - ``/api/auth/register``
     - guest
     - create a guest account
   * - ``POST``
     - ``/api/auth/login``
     - guest or staff
     - create an authenticated session
   * - ``POST``
     - ``/api/auth/logout``
     - guest or staff
     - end the current authenticated session
   * - ``GET``
     - ``/api/auth/session``
     - guest or staff
     - return the authenticated user and staff context

Rooms And Availability
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``GET``
     - ``/api/rooms/availability``
     - guest
     - search available rooms by date range and guest count
   * - ``GET``
     - ``/api/rooms/{room_id}``
     - guest
     - fetch one room detail record
   * - ``GET``
     - ``/api/staff/rooms``
     - staff
     - list rooms with internal status and filters
   * - ``PATCH``
     - ``/api/staff/rooms/{room_id}/status``
     - staff
     - update room status within allowed transitions

Bookings
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``POST``
     - ``/api/bookings``
     - guest
     - create a booking after quote acceptance
   * - ``GET``
     - ``/api/bookings``
     - guest
     - list the guest's bookings
   * - ``GET``
     - ``/api/bookings/{booking_id}``
     - guest or staff
     - return booking detail
   * - ``POST``
     - ``/api/bookings/{booking_id}/cancel``
     - guest or staff
     - cancel a booking within policy
   * - ``GET``
     - ``/api/bookings/{booking_id}/check-in-readiness``
     - guest or staff
     - return arrival or check-in readiness
   * - ``POST``
     - ``/api/staff/bookings/{booking_id}/check-in-verify``
     - staff
     - validate a guest check-in
   * - ``POST``
     - ``/api/bookings/{booking_id}/checkout``
     - guest or staff
     - register checkout and trigger downstream turnover flow

Services And Service Bookings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``GET``
     - ``/api/services``
     - guest
     - list service catalog entries
   * - ``GET``
     - ``/api/service-categories``
     - guest
     - list service categories
   * - ``POST``
     - ``/api/service-bookings``
     - guest
     - create a scheduled service booking
   * - ``GET``
     - ``/api/service-bookings``
     - guest or staff
     - list service bookings by booking or guest
   * - ``PATCH``
     - ``/api/service-bookings/{service_booking_id}/status``
     - staff
     - update booking status

Service Requests
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``POST``
     - ``/api/service-requests``
     - guest or staff
     - create an in-stay request
   * - ``GET``
     - ``/api/service-requests``
     - guest or staff
     - list service requests in actor scope
   * - ``GET``
     - ``/api/service-requests/{service_request_id}``
     - guest or staff
     - fetch one request
   * - ``PATCH``
     - ``/api/service-requests/{service_request_id}/status``
     - staff
     - move request through allowed status transitions

Notifications
^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``GET``
     - ``/api/notifications``
     - guest or staff
     - list notifications in actor scope
   * - ``GET``
     - ``/api/notifications/{notification_id}``
     - guest or staff
     - fetch one notification detail

Conversation And Agent Interaction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These endpoints are public even though the agent itself is private. The backend
receives the request and then calls the internal agent service.

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``POST``
     - ``/api/chat/messages``
     - guest or staff
     - send one message and receive an assistant response or proposal
   * - ``GET``
     - ``/api/chat/conversations/{conversation_id}``
     - guest or staff
     - fetch conversation header state
   * - ``GET``
     - ``/api/chat/conversations/{conversation_id}/messages``
     - guest or staff
     - fetch transcript messages
   * - ``POST``
     - ``/api/proposals/{proposal_id}/confirm``
     - guest or staff
     - confirm an agent-generated proposal
   * - ``POST``
     - ``/api/proposals/{proposal_id}/reject``
     - guest or staff
     - reject an agent-generated proposal

Escalations And Staff Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 36 16 36

   * - Method
     - Path
     - Actor
     - Purpose
   * - ``GET``
     - ``/api/staff/housekeeping/queue``
     - housekeeping or manager
     - list prioritized turnover queue
   * - ``GET``
     - ``/api/staff/assignments``
     - staff or manager
     - list assignments in scope
   * - ``PATCH``
     - ``/api/staff/assignments/{assignment_id}/status``
     - staff or manager
     - update assignment state
   * - ``GET``
     - ``/api/escalations``
     - manager or admin
     - list escalation cases
   * - ``PATCH``
     - ``/api/escalations/{escalation_id}/status``
     - manager or admin
     - move escalation state

Critical Request And Response Shapes
------------------------------------
These shapes should be frozen first because they unblock the most frontend and
backend work.

``POST /api/chat/messages``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Request:

.. code-block:: json

   {
     "conversation_id": "conv_001",
     "booking_id": "booking_123",
     "content": "I need two extra towels.",
     "channel": "mobile_chat",
     "language": "en"
   }

Response:

.. code-block:: json

   {
     "data": {
       "conversation_id": "conv_001",
       "message_id": "msg_010",
       "assistant_message": {
         "role": "assistant",
         "content": "I can request two extra towels for your room."
       },
       "proposals": [
         {
           "id": "prop_001",
           "tool_name": "create_service_request",
           "action_summary": "Create housekeeping request for two extra towels",
           "status": "presented",
           "expires_at": "2026-04-10T18:30:00Z"
         }
       ],
       "handover": null
     },
     "meta": {
       "request_id": "req_123"
     }
   }

``POST /api/bookings``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Request:

.. code-block:: json

   {
     "room_id": "room_101",
     "check_in_date": "2026-04-10",
     "check_out_date": "2026-04-13",
     "adults": 2,
     "children": 1,
     "special_requests": "Quiet room if possible",
     "proposal_id": "prop_101"
   }

Response:

.. code-block:: json

   {
     "data": {
       "id": "booking_123",
       "status": "confirmed",
       "room_id": "room_101",
       "resort_id": "resort_1",
       "check_in_date": "2026-04-10",
       "check_out_date": "2026-04-13",
       "total_price_cents": 54000
     },
     "meta": {
       "request_id": "req_124"
     }
   }

``POST /api/service-requests``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Request:

.. code-block:: json

   {
     "booking_id": "booking_123",
     "type": "housekeeping",
     "description": "Need two extra towels",
     "requested_for_time": "2026-04-10T18:30:00Z",
     "proposal_id": "prop_001"
   }

Response:

.. code-block:: json

   {
     "data": {
       "id": "sr_101",
       "booking_id": "booking_123",
       "type": "housekeeping",
       "description": "Need two extra towels",
       "status": "open",
       "priority": "p3_standard",
       "requested_at": "2026-04-10T18:12:00Z"
     },
     "meta": {
       "request_id": "req_125"
     }
   }

``POST /api/proposals/{proposal_id}/confirm``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Request:

.. code-block:: json

   {
     "note": "confirmed by guest"
   }

Response:

.. code-block:: json

   {
     "data": {
       "proposal_id": "prop_001",
       "status": "executed",
       "resource_type": "service_request",
       "resource_id": "sr_101"
     },
     "meta": {
       "request_id": "req_126"
     }
   }

Open Decisions
--------------
The backend and frontend teams should still confirm these before implementation
starts:

* whether list endpoints use page/page_size or cursor-based pagination - cursor-based pagination.
* whether ``/api/chat/messages`` returns a synchronous response, SSE stream, or
  both - for now synchronous response in future maybe we can add SSE for streaming assistant messages and proposals.
* whether service bookings and service requests are both guest-visible in v1 - only service bookings are guest visible.
* whether checkout is guest-initiated in phase 1 or staff-mediated only - guest intiated in phase 1
