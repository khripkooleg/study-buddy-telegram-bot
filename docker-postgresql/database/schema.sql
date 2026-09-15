create table if not exists users (
    id                  bigserial primary key,
    telegram_id         bigint not null unique,
    username            varchar(50),
    created_at          timestamptz not null default current_timestamp
);

create table if not exists profiles (
    id                  bigserial primary key,
    user_id             bigint not null unique references users(id) on delete cascade,
    name                varchar(50) not null,
    faculty             varchar(100) not null,
    degree              varchar(25) not null,
    subject             varchar(50) not null,
    goal                text,
    is_active           boolean not null default true
);

create index if not exists idx_profiles_match
    on profiles (faculty, degree, subject)
    where is_active;

create table if not exists likes (
    id                  bigserial primary key,
    liker_profile_id    bigint not null references profiles(id) on delete cascade,
    liked_profile_id    bigint not null references profiles(id) on delete cascade,
    created_at          timestamptz not null default current_timestamp,
    constraint unique_like unique (liker_profile_id, liked_profile_id),
    constraint no_self_like check (liker_profile_id <> liked_profile_id)
);
