-- Seed real UUID-backed facility rooms/devices.
-- Synthetic IDs such as default-room-* must never be sent as room_id/device_id.

create extension if not exists pgcrypto;

alter table if exists public.facility_rooms
  add column if not exists slug text;

alter table if exists public.facility_devices
  add column if not exists slug text,
  add column if not exists device_type text default 'room_temp',
  add column if not exists target_temperature numeric,
  add column if not exists threshold_temp numeric,
  add column if not exists type text,
  add column if not exists is_default boolean not null default false,
  add column if not exists is_active boolean not null default true;

create unique index if not exists uq_facility_rooms_slug_013
on public.facility_rooms (slug);

create unique index if not exists uq_facility_devices_room_slug_013
on public.facility_devices (room_id, slug);

with room_seed(name, slug, description) as (
  values
    ('PPIC', 'ppic', 'Default monitoring room'),
    ('Grouper', 'grouper', 'Default monitoring room'),
    ('Pack Basah', 'pack-basah', 'Default monitoring room'),
    ('Pack Kering', 'pack-kering', 'Default monitoring room'),
    ('Ruang Kopi', 'ruang-kopi', 'Default monitoring room'),
    ('Kitchen', 'kitchen', 'Default monitoring room')
)
insert into public.facility_rooms (name, slug, description, is_active)
select name, slug, description, true
from room_seed
on conflict (slug) do nothing;

with device_seed(name, slug, device_type, target_temperature) as (
  values
    ('Suhu Ruangan', 'suhu-ruangan', 'room_temp', 25::numeric),
    ('Chiller', 'chiller', 'chiller', 5::numeric),
    ('Freezer', 'freezer', 'freezer', -18::numeric)
)
insert into public.facility_devices (
  room_id,
  name,
  slug,
  device_type,
  type,
  target_temperature,
  threshold_temp,
  is_default,
  is_active
)
select
  room.id,
  device_seed.name,
  device_seed.slug,
  device_seed.device_type,
  device_seed.device_type,
  device_seed.target_temperature,
  device_seed.target_temperature,
  true,
  true
from public.facility_rooms room
cross join device_seed
where room.slug in ('ppic', 'grouper', 'pack-basah', 'pack-kering', 'ruang-kopi', 'kitchen')
on conflict (room_id, slug) do nothing;
