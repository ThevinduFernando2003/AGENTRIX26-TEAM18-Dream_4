-- MedBridge AI schema. Tier 1 builds against this; Tier 2/3 tables are
-- defined now so later phases don't churn the schema.
--
-- Migrations: `CREATE TABLE IF NOT EXISTS` is a no-op against existing
-- DBs. To pick up schema changes (e.g. the AppointmentSlot UNIQUE
-- constraint), delete project/db/app.db and let init_db() rebuild.

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
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ChatMessage (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES User(user_id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content    TEXT NOT NULL,
    timestamp  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_user_time ON ChatMessage(user_id, timestamp);

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
    is_available INTEGER NOT NULL DEFAULT 1,
    UNIQUE(doctor_id, date, time)
);
-- The UNIQUE constraint above implies an index on (doctor_id, date, time),
-- so the previous explicit idx_slot_doctor_date is redundant and removed.

CREATE TABLE IF NOT EXISTS Appointment (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES User(user_id),
    slot_id        INTEGER NOT NULL UNIQUE REFERENCES AppointmentSlot(slot_id),
    status         TEXT NOT NULL DEFAULT 'confirmed',
    booked_at      TEXT DEFAULT (datetime('now'))
);

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
