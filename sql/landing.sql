-- =====================================================================
--  Landing: seccion de videos (Stream HUD) y contador de visitas
--  Ejecutar completo en: Supabase Dashboard > SQL Editor
--
--  Decisiones de diseno:
--   * La lectura de videos es publica SOLO si estan activos. No hay
--     policies de escritura: escribe unicamente service_role (defensa en
--     profundidad; el rol admin tambien se valida en app_metadata).
--   * El contador se incrementa con una RPC atomica. Un SELECT + UPDATE
--     desde Python permitiria perder visitas por carrera.
--   * Guardamos la URL, no el video: YouTube se renderiza en iframe y
--     Supabase Storage en <video>. El servidor valida el host antes de
--     devolverla al navegador (lista blanca, nunca HTML crudo).
-- =====================================================================

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------
-- Contenido curado por el admin
-- ---------------------------------------------------------------------
create table if not exists public.videos (
    id             uuid primary key default gen_random_uuid(),
    slug           text not null unique,
    title          text not null,
    description    text,
    categoria      text not null,
    video_url      text not null,
    poster_url     text,
    duration_label text,
    is_active      boolean not null default true,
    published_at   timestamptz not null default now(),
    created_at     timestamptz not null default now()
);

create index if not exists videos_publicos_idx
    on public.videos (is_active, categoria, published_at desc);

alter table public.videos enable row level security;

drop policy if exists "videos publicos activos" on public.videos;
create policy "videos publicos activos" on public.videos
    for select to anon, authenticated
    using (is_active = true);
-- SIN policies de INSERT / UPDATE / DELETE: solo service_role escribe.

-- ---------------------------------------------------------------------
-- Contador de visitas: una sola fila, incremento atomico
-- ---------------------------------------------------------------------
create table if not exists public.landing_visits (
    id         smallint primary key default 1 check (id = 1),
    total      bigint not null default 0,
    updated_at timestamptz not null default now()
);

alter table public.landing_visits enable row level security;
-- Sin policies: nadie anonimo lee ni escribe esta tabla.

create or replace function public.register_landing_visit()
returns bigint
language sql
security definer
set search_path = public
as $$
    insert into public.landing_visits (id, total) values (1, 1)
    on conflict (id) do update
        set total = landing_visits.total + 1,
            updated_at = now()
    returning total;
$$;

revoke all on function public.register_landing_visit() from public, anon, authenticated;
grant execute on function public.register_landing_visit() to service_role;

-- ---------------------------------------------------------------------
-- Ejemplo de carga (NO ejecutar: el admin lo agrega desde /admin/videos)
-- ---------------------------------------------------------------------
-- insert into public.videos
--     (slug, title, categoria, video_url, poster_url, duration_label, description)
-- values
--     ('charla-fastapi', 'Charla: FastAPI en produccion', 'charla',
--      'https://www.youtube.com/watch?v=dQw4w9WgXcQ', NULL, '18:42',
--      'Como estructuramos una API en capas.');
