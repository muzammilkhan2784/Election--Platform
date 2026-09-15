CREATE TYPE user_role AS ENUM ('member', 'officer', 'employee', 'admin');
CREATE TYPE user_status AS ENUM ('active', 'invited', 'disabled');
CREATE TYPE election_status AS ENUM ('draft', 'active', 'completed');

CREATE TABLE society (
    society_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "user" (
    user_id SERIAL PRIMARY KEY,
    society_id INT REFERENCES society(society_id),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role user_role NOT NULL,
    status user_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE employee_society_assignment (
    assignment_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
    society_id INT NOT NULL REFERENCES society(society_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, society_id)
);

CREATE TABLE session (
    session_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(100)
);

CREATE TABLE election (
    election_id SERIAL PRIMARY KEY,
    society_id INT NOT NULL REFERENCES society(society_id) ON DELETE CASCADE,
    created_by INT NOT NULL REFERENCES "user"(user_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    instructions TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status election_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_election_dates CHECK (end_date >= start_date)
);

CREATE TABLE office (
    office_id SERIAL PRIMARY KEY,
    election_id INT NOT NULL REFERENCES election(election_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    votes_allowed INT NOT NULL DEFAULT 1,
    allow_write_in BOOLEAN NOT NULL DEFAULT FALSE,
    display_order INT NOT NULL DEFAULT 1,
    CONSTRAINT chk_votes_allowed CHECK (votes_allowed > 0)
);

CREATE TABLE candidate (
    candidate_id SERIAL PRIMARY KEY,
    office_id INT NOT NULL REFERENCES office(office_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    title_position VARCHAR(255),
    biography TEXT,
    photo_url TEXT,
    display_order INT NOT NULL DEFAULT 1
);

CREATE TABLE vote (
    vote_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
    election_id INT NOT NULL REFERENCES election(election_id) ON DELETE CASCADE,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(100),
    UNIQUE (user_id, election_id)
);

CREATE TABLE candidate_vote (
    candidate_vote_id SERIAL PRIMARY KEY,
    vote_id INT NOT NULL REFERENCES vote(vote_id) ON DELETE CASCADE,
    office_id INT NOT NULL REFERENCES office(office_id) ON DELETE CASCADE,
    candidate_id INT REFERENCES candidate(candidate_id) ON DELETE CASCADE,
    write_in_name VARCHAR(255),
    CONSTRAINT chk_candidate_or_writein CHECK (
        (candidate_id IS NOT NULL AND write_in_name IS NULL)
        OR
        (candidate_id IS NULL AND write_in_name IS NOT NULL)
    )
);

CREATE TABLE initiative (
    initiative_id SERIAL PRIMARY KEY,
    election_id INT NOT NULL REFERENCES election(election_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    display_order INT NOT NULL DEFAULT 1
);

CREATE TABLE initiative_option (
    option_id SERIAL PRIMARY KEY,
    initiative_id INT NOT NULL REFERENCES initiative(initiative_id) ON DELETE CASCADE,
    label VARCHAR(255) NOT NULL,
    display_order INT NOT NULL DEFAULT 1
);

CREATE TABLE initiative_vote (
    initiative_vote_id SERIAL PRIMARY KEY,
    vote_id INT NOT NULL REFERENCES vote(vote_id) ON DELETE CASCADE,
    initiative_id INT NOT NULL REFERENCES initiative(initiative_id) ON DELETE CASCADE,
    option_id INT NOT NULL REFERENCES initiative_option(option_id) ON DELETE CASCADE,
    UNIQUE (vote_id, initiative_id)
);

CREATE TABLE vote_draft (
    draft_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
    election_id INT NOT NULL REFERENCES election(election_id) ON DELETE CASCADE,
    payload_json JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, election_id)
);

CREATE TABLE ballot_edit_audit (
    audit_id SERIAL PRIMARY KEY,
    election_id INT NOT NULL REFERENCES election(election_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES "user"(user_id),
    action VARCHAR(255) NOT NULL,
    details TEXT,
    edited_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_society_id ON "user"(society_id);
CREATE INDEX idx_employee_assignment_user_id ON employee_society_assignment(user_id);
CREATE INDEX idx_employee_assignment_society_id ON employee_society_assignment(society_id);
CREATE INDEX idx_session_user_id ON session(user_id);
CREATE INDEX idx_session_expires_at ON session(expires_at);
CREATE INDEX idx_election_society_id ON election(society_id);
CREATE INDEX idx_election_created_by ON election(created_by);
CREATE INDEX idx_election_status ON election(status);
CREATE INDEX idx_election_dates ON election(start_date, end_date);
CREATE INDEX idx_office_election_id ON office(election_id);
CREATE INDEX idx_candidate_office_id ON candidate(office_id);
CREATE INDEX idx_vote_user_id ON vote(user_id);
CREATE INDEX idx_vote_election_id ON vote(election_id);
CREATE INDEX idx_candidate_vote_vote_id ON candidate_vote(vote_id);
CREATE INDEX idx_candidate_vote_office_id ON candidate_vote(office_id);
CREATE INDEX idx_candidate_vote_candidate_id ON candidate_vote(candidate_id);
CREATE INDEX idx_initiative_election_id ON initiative(election_id);
CREATE INDEX idx_initiative_option_initiative_id ON initiative_option(initiative_id);
CREATE INDEX idx_initiative_vote_vote_id ON initiative_vote(vote_id);
CREATE INDEX idx_initiative_vote_initiative_id ON initiative_vote(initiative_id);
CREATE INDEX idx_initiative_vote_option_id ON initiative_vote(option_id);
CREATE INDEX idx_vote_draft_user_id ON vote_draft(user_id);
CREATE INDEX idx_vote_draft_election_id ON vote_draft(election_id);
CREATE INDEX idx_ballot_edit_audit_election_id ON ballot_edit_audit(election_id);
CREATE INDEX idx_ballot_edit_audit_user_id ON ballot_edit_audit(user_id);
CREATE INDEX idx_ballot_edit_audit_edited_at ON ballot_edit_audit(edited_at);