CREATE TYPE "room_type" AS ENUM (
  'standard',
  'superior',
  'deluxe',
  'suite',
  'presidential'
);

CREATE TYPE "room_status" AS ENUM (
  'available',
  'booked',
  'occupied',
  'needs_cleaning',
  'in_maintenance'
);

CREATE TYPE "amenity_category" AS ENUM (
  'view',
  'technology',
  'comfort',
  'bathroom',
  'outdoor'
);

CREATE TYPE "reservation_status" AS ENUM (
  'confirmed',
  'checked_in',
  'checked_out',
  'cancelled',
  'no_show'
);

CREATE TYPE "service_booking_status" AS ENUM (
  'pending',
  'confirmed',
  'completed',
  'cancelled'
);

CREATE TYPE "service_request_status" AS ENUM (
  'open',
  'in_progress',
  'resolved',
  'cancelled'
);

CREATE TYPE "service_request_type" AS ENUM (
  'housekeeping',
  'maintenance',
  'food_beverage',
  'concierge',
  'other'
);

CREATE TYPE "notification_channel" AS ENUM (
  'email',
  'push',
  'dashboard'
);

CREATE TYPE "notification_status" AS ENUM (
  'pending',
  'sent',
  'failed'
);

CREATE TYPE "notification_event" AS ENUM (
  'reservation_confirmed',
  'reservation_cancelled',
  'check_in_reminder',
  'checkout_reminder',
  'no_show_flagged',
  'new_reservation_created',
  'room_needs_cleaning',
  'room_in_maintenance',
  'room_available',
  'service_booking_confirmed',
  'service_request_resolved'
);

CREATE TABLE "user" (
  "id" text PRIMARY KEY,
  "name" text NOT NULL,
  "email" text UNIQUE NOT NULL,
  "email_verified" boolean NOT NULL DEFAULT false,
  "image" text,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "session" (
  "id" text PRIMARY KEY,
  "user_id" text NOT NULL,
  "token" text UNIQUE NOT NULL,
  "expires_at" timestamp NOT NULL,
  "ip_address" text,
  "user_agent" text,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "account" (
  "id" text PRIMARY KEY,
  "user_id" text NOT NULL,
  "account_id" text NOT NULL,
  "provider_id" text NOT NULL,
  "access_token" text,
  "refresh_token" text,
  "id_token" text,
  "access_token_expires_at" timestamp,
  "refresh_token_expires_at" timestamp,
  "scope" text,
  "password" text,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "verification" (
  "id" text PRIMARY KEY,
  "identifier" text NOT NULL,
  "value" text NOT NULL,
  "expires_at" timestamp NOT NULL,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "resort" (
  "id" text PRIMARY KEY,
  "name" text NOT NULL,
  "location" text NOT NULL,
  "currency" text NOT NULL DEFAULT 'USD',
  "check_in_time" text NOT NULL DEFAULT '14:00',
  "check_out_time" text NOT NULL DEFAULT '12:00',
  "max_nights" integer NOT NULL DEFAULT 90,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "room" (
  "id" text PRIMARY KEY,
  "resort_id" text NOT NULL,
  "room_number" text NOT NULL,
  "type" room_type NOT NULL,
  "floor" integer,
  "size_sqm" decimal,
  "max_guests" integer NOT NULL,
  "bed_configuration" text,
  "status" room_status NOT NULL DEFAULT 'available',
  "base_price_cents" integer NOT NULL,
  "accessible" boolean NOT NULL DEFAULT false,
  "notes" text,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "amenity" (
  "id" text PRIMARY KEY,
  "name" text NOT NULL,
  "category" amenity_category NOT NULL,
  "icon_slug" text NOT NULL,
  "created_at" timestamp NOT NULL
);

CREATE TABLE "room_amenity" (
  "room_id" text NOT NULL,
  "amenity_id" text NOT NULL,
  PRIMARY KEY ("room_id", "amenity_id")
);

CREATE TABLE "room_status_log" (
  "id" text PRIMARY KEY,
  "room_id" text NOT NULL,
  "previous_status" room_status,
  "new_status" room_status NOT NULL,
  "changed_by" text NOT NULL,
  "reason" text,
  "changed_at" timestamp NOT NULL
);

CREATE TABLE "room_image" (
  "id" text PRIMARY KEY,
  "room_id" text NOT NULL,
  "url" text NOT NULL,
  "caption" text,
  "sort_order" integer NOT NULL DEFAULT 0,
  "created_at" timestamp NOT NULL
);

CREATE TABLE "reservation" (
  "id" text PRIMARY KEY,
  "user_id" text NOT NULL,
  "room_id" text NOT NULL,
  "resort_id" text NOT NULL,
  "check_in_date" date NOT NULL,
  "check_out_date" date NOT NULL,
  "adults" integer NOT NULL DEFAULT 1,
  "children" integer NOT NULL DEFAULT 0,
  "status" reservation_status NOT NULL DEFAULT 'confirmed',
  "total_price_cents" integer NOT NULL,
  "special_requests" text,
  "cancellation_reason" text,
  "cancelled_at" timestamp,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "reservation_audit_log" (
  "id" text PRIMARY KEY,
  "reservation_id" text NOT NULL,
  "changed_by" text NOT NULL,
  "previous_status" reservation_status,
  "new_status" reservation_status NOT NULL,
  "change_reason" text,
  "changed_at" timestamp NOT NULL
);

CREATE TABLE "service_category" (
  "id" text PRIMARY KEY,
  "name" text NOT NULL,
  "slug" text UNIQUE NOT NULL,
  "created_at" timestamp NOT NULL
);

CREATE TABLE "service" (
  "id" text PRIMARY KEY,
  "category_id" text NOT NULL,
  "name" text NOT NULL,
  "description" text,
  "price_cents" integer NOT NULL,
  "duration_mins" integer,
  "available" boolean NOT NULL DEFAULT true,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "service_booking" (
  "id" text PRIMARY KEY,
  "reservation_id" text NOT NULL,
  "service_id" text NOT NULL,
  "status" service_booking_status NOT NULL DEFAULT 'pending',
  "scheduled_at" timestamp,
  "quantity" integer NOT NULL DEFAULT 1,
  "total_price_cents" integer NOT NULL,
  "notes" text,
  "created_at" timestamp NOT NULL,
  "updated_at" timestamp NOT NULL
);

CREATE TABLE "service_request" (
  "id" text PRIMARY KEY,
  "reservation_id" text NOT NULL,
  "assigned_to" text,
  "type" service_request_type NOT NULL,
  "description" text NOT NULL,
  "status" service_request_status NOT NULL DEFAULT 'open',
  "requested_at" timestamp NOT NULL,
  "resolved_at" timestamp
);

CREATE TABLE "notification" (
  "id" text PRIMARY KEY,
  "reservation_id" text,
  "user_id" text NOT NULL,
  "event" notification_event NOT NULL,
  "channel" notification_channel NOT NULL,
  "status" notification_status NOT NULL DEFAULT 'pending',
  "failure_reason" text,
  "sent_at" timestamp,
  "created_at" timestamp NOT NULL
);

CREATE INDEX ON "session" ("user_id");

CREATE INDEX ON "account" ("user_id");

CREATE INDEX ON "verification" ("identifier");

CREATE INDEX ON "resort" ("name");

CREATE UNIQUE INDEX ON "room" ("resort_id", "room_number");

CREATE INDEX ON "room" ("resort_id", "status");

CREATE INDEX ON "room" ("resort_id", "type", "status");

ALTER TABLE "session" ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "account" ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "room" ADD FOREIGN KEY ("resort_id") REFERENCES "resort" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "room_amenity" ADD FOREIGN KEY ("room_id") REFERENCES "room" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "room_amenity" ADD FOREIGN KEY ("amenity_id") REFERENCES "amenity" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "room_status_log" ADD FOREIGN KEY ("room_id") REFERENCES "room" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "room_status_log" ADD FOREIGN KEY ("changed_by") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "room_image" ADD FOREIGN KEY ("room_id") REFERENCES "room" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "reservation" ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "reservation" ADD FOREIGN KEY ("room_id") REFERENCES "room" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "reservation" ADD FOREIGN KEY ("resort_id") REFERENCES "resort" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "reservation_audit_log" ADD FOREIGN KEY ("reservation_id") REFERENCES "reservation" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "reservation_audit_log" ADD FOREIGN KEY ("changed_by") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "service" ADD FOREIGN KEY ("category_id") REFERENCES "service_category" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "service_booking" ADD FOREIGN KEY ("reservation_id") REFERENCES "reservation" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "service_booking" ADD FOREIGN KEY ("service_id") REFERENCES "service" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "service_request" ADD FOREIGN KEY ("reservation_id") REFERENCES "reservation" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "service_request" ADD FOREIGN KEY ("assigned_to") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "notification" ADD FOREIGN KEY ("reservation_id") REFERENCES "reservation" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "notification" ADD FOREIGN KEY ("user_id") REFERENCES "user" ("id") DEFERRABLE INITIALLY IMMEDIATE;
