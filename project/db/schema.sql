-- MedBridge AI schema. Tier 1 builds against this; Tier 2/3 tables are
-- defined now so later phases don't churn the schema.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS User (
    user_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username             TEXT NOT NULL UNIQUE,
    password_hash        TEXT NOT NULL,
    full_name            TEXT,
    age                  INTEGER,
    gender               TEXT,
    preferred_language   TEXT DEFAULT 'en',
    family_contact_name  TEXT,
    family_contact_phone TEXT,
    -- PDPA-style health-data processing consent (ISO timestamp); required for new signups.
    consent_accepted_at  TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- A chat "thread" (ChatGPT-style). Messages belong to one conversation so the
-- sidebar can list past chats and start new ones.
CREATE TABLE IF NOT EXISTS Conversation (
    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES User(user_id) ON DELETE CASCADE,
    title           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_conv_user ON Conversation(user_id, conversation_id);

CREATE TABLE IF NOT EXISTS ChatMessage (
    message_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES User(user_id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES Conversation(conversation_id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content         TEXT NOT NULL,
    timestamp       TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_user_time ON ChatMessage(user_id, timestamp);
-- idx_chat_conversation is created in db._migrate(), AFTER the conversation_id
-- column is guaranteed to exist (it's absent on DBs created before this change).

CREATE TABLE IF NOT EXISTS MedicalReport (
    report_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES User(user_id) ON DELETE CASCADE,
    file_url    TEXT,
    ocr_text    TEXT,
    uploaded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS SpecialistOpinion (
    opinion_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id       INTEGER NOT NULL REFERENCES MedicalReport(report_id) ON DELETE CASCADE,
    specialist_type TEXT NOT NULL,
    findings        TEXT,
    confidence      REAL,
    flags           TEXT
);

CREATE TABLE IF NOT EXISTS ConsensusReport (
    consensus_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id           INTEGER NOT NULL REFERENCES MedicalReport(report_id) ON DELETE CASCADE,
    summary             TEXT,
    disagreement_notes  TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Specialty (
    specialty_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS Facility (
    facility_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    type        TEXT,
    address     TEXT,
    lat         REAL,
    lng         REAL,
    phone       TEXT
);

CREATE TABLE IF NOT EXISTS Doctor (
    doctor_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id    INTEGER NOT NULL REFERENCES Facility(facility_id),
    specialty_id   INTEGER NOT NULL REFERENCES Specialty(specialty_id),
    name           TEXT NOT NULL,
    channeling_fee REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS AppointmentSlot (
    slot_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id    INTEGER NOT NULL REFERENCES Doctor(doctor_id),
    date         TEXT NOT NULL,
    time         TEXT NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_slot_doctor_date ON AppointmentSlot(doctor_id, date);

CREATE TABLE IF NOT EXISTS Appointment (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES User(user_id),
    -- slot_id is not globally UNIQUE: cancelled rows keep history; only one
    -- confirmed appointment may hold a slot (see idx_appt_slot_confirmed).
    slot_id        INTEGER NOT NULL REFERENCES AppointmentSlot(slot_id),
    status         TEXT NOT NULL DEFAULT 'confirmed',
    booked_at      TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_appt_slot_confirmed
    ON Appointment(slot_id) WHERE status = 'confirmed';

CREATE TABLE IF NOT EXISTS FutureVisitReminder (
    reminder_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                INTEGER NOT NULL REFERENCES User(user_id),
    doctor_id              INTEGER REFERENCES Doctor(doctor_id),
    target_date_or_month   TEXT,
    notified               INTEGER NOT NULL DEFAULT 0,
    created_at             TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Prescription (
    prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES User(user_id),
    input_type      TEXT NOT NULL CHECK (input_type IN ('text','photo')),
    ocr_text        TEXT,
    user_confirmed  INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Medicine (
    medicine_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name                   TEXT NOT NULL UNIQUE,
    reference_dosage_text  TEXT
);

CREATE TABLE IF NOT EXISTS Pharmacy (
    pharmacy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    address     TEXT,
    lat         REAL,
    lng         REAL
);

CREATE TABLE IF NOT EXISTS PharmacyMedicinePrice (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_id INTEGER NOT NULL REFERENCES Pharmacy(pharmacy_id),
    medicine_id INTEGER NOT NULL REFERENCES Medicine(medicine_id),
    price       REAL NOT NULL,
    in_stock    INTEGER NOT NULL DEFAULT 1,
    -- Phase 0: bumped on every supplier edit; seed rows get created_at-style stamp.
    updated_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(pharmacy_id, medicine_id)
);

CREATE TABLE IF NOT EXISTS NotificationLog (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER REFERENCES User(user_id),
    type     TEXT NOT NULL,
    message  TEXT,
    channel  TEXT NOT NULL,
    sent_at  TEXT DEFAULT (datetime('now'))
);
