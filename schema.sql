-- WorkLog PostgreSQL schema v1
-- Execute in a newly created worklog_db database.

CREATE TABLE app_user (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT users_username_not_blank CHECK (length(btrim(username)) > 0)
);

CREATE TABLE work_setting (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES app_user(id) ON DELETE CASCADE,
    default_clock_in TIME NOT NULL DEFAULT '09:00',
    default_clock_out TIME NOT NULL DEFAULT '18:00',
    default_break_start TIME DEFAULT '12:00',
    default_break_end TIME DEFAULT '13:00',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT settings_work_order CHECK (default_clock_in < default_clock_out),
    CONSTRAINT settings_break_order CHECK (
        (default_break_start IS NULL AND default_break_end IS NULL)
        OR (default_break_start IS NOT NULL AND default_break_end IS NOT NULL
            AND default_clock_in <= default_break_start
            AND default_break_start < default_break_end
            AND default_break_end <= default_clock_out)
    )
);

CREATE TABLE work_record (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    clock_in TIME NOT NULL,
    clock_out TIME NOT NULL,
    break_start TIME,
    break_end TIME,
    memo TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT attendance_one_per_day UNIQUE (user_id, work_date),
    CONSTRAINT attendance_work_order CHECK (clock_in < clock_out),
    CONSTRAINT attendance_break_order CHECK (
        (break_start IS NULL AND break_end IS NULL)
        OR (break_start IS NOT NULL AND break_end IS NOT NULL
            AND clock_in <= break_start
            AND break_start < break_end
            AND break_end <= clock_out)
    )
);

CREATE TABLE paid_leave_grant (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    granted_date DATE NOT NULL,
    granted_days NUMERIC(4,1) NOT NULL,
    expires_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT grants_positive_days CHECK (granted_days > 0 AND mod(granted_days, 0.5) = 0),
    CONSTRAINT grants_valid_dates CHECK (expires_date >= granted_date),
    CONSTRAINT grants_id_user_unique UNIQUE (id, user_id)
);

CREATE TABLE paid_leave_usage (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    grant_id INTEGER NOT NULL,
    leave_date DATE NOT NULL,
    used_days NUMERIC(3,1) NOT NULL,
    leave_type VARCHAR(10) NOT NULL,
    memo TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT usage_grant_same_user FOREIGN KEY (grant_id, user_id)
        REFERENCES paid_leave_grant(id, user_id) ON DELETE RESTRICT,
    CONSTRAINT usage_type_days_match CHECK (
        (leave_type = 'FULL' AND used_days = 1.0)
        OR (leave_type IN ('AM', 'PM') AND used_days = 0.5)
    ),
    CONSTRAINT usage_one_per_day UNIQUE (user_id, leave_date)
);

CREATE INDEX attendance_user_date_idx ON work_record(user_id, work_date DESC);
CREATE INDEX leave_grants_user_dates_idx ON paid_leave_grant(user_id, granted_date, expires_date);
CREATE INDEX leave_usage_grant_idx ON paid_leave_usage(grant_id);

-- PostgreSQL DEFAULT NOW() only covers inserts; this trigger covers updates.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON app_user
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER user_settings_updated_at BEFORE UPDATE ON work_setting
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER attendance_updated_at BEFORE UPDATE ON work_record
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER leave_grants_updated_at BEFORE UPDATE ON paid_leave_grant
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER leave_usage_updated_at BEFORE UPDATE ON paid_leave_usage
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
