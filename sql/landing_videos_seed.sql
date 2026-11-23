-- =====================================================================
--  Seed de videos de la landing (Stream HUD)
--  Ejecutar DESPUES de sql/landing.sql en el SQL Editor de Supabase.
--
--  * Los titulos se obtuvieron del endpoint publico oEmbed de YouTube,
--    no se inventaron.
--  * Las URLs se normalizaron a watch?v=... (se quitaron los ?si= de
--    tracking de los links compartidos). El validador del backend sigue
--    aceptando igual las tres formas: watch, youtu.be y embed.
--  * duration_label queda NULL porque oEmbed NO expone duracion. Se puede
--    completar desde /admin/videos cuando se conozca.
--  * published_at se escalona con intervalos para que el orden de la grilla
--    (order by published_at desc) respete el orden en que se entregaron los
--    links. No es la fecha real de publicacion: es solo orden de muestra.
--  * ON CONFLICT hace que correr este archivo dos veces no duplique nada.
-- =====================================================================

insert into public.videos
    (slug, title, categoria, video_url, description, duration_label, is_active, published_at)
values
    (
        'blue-lobster-jumpscare',
        'Blue Lobster Jumpscare (SCARY!)',
        'curiosidades',
        'https://www.youtube.com/watch?v=5UlK_vJzTOk',
        'Canal: regrins.',
        null,
        true,
        now() - interval '6 seconds'
    ),
    (
        'smash-ultimate-turning-point-final',
        'The Turning Point GRAND FINALS - LeoN (Bowser) Vs. Butter (Luigi) - SSBU',
        'torneos',
        'https://www.youtube.com/watch?v=3Ean6FL8bCY',
        'Canal: VGBootCamp.',
        null,
        true,
        now() - interval '5 seconds'
    ),
    (
        'smash-ultimate-lmbm-2025-kola-vs-jeja',
        'LMBM 2025 - Kola (Roy) Vs. JeJaJeJa (Kirby) - SSBU',
        'torneos',
        'https://www.youtube.com/watch?v=nj-kx-RqXek',
        'Canal: VGBootCamp.',
        null,
        true,
        now() - interval '4 seconds'
    ),
    (
        'smash-ultimate-ssc-2023-acola-vs-riddles',
        'SSC 2023 Winners Quarters - acola (Steve) Vs. Riddles (Kazuya) - SSBU',
        'torneos',
        'https://www.youtube.com/watch?v=e4yIvqQT10Y',
        'Canal: VGBootCamp.',
        null,
        true,
        now() - interval '3 seconds'
    ),
    (
        'mario-64-tas-0-star',
        'Super Mario 64 (TAS) 0 star run in 1:21.54',
        'demos',
        'https://www.youtube.com/watch?v=W-MrhVPEqRo',
        'Canal: SuperLuigiGlitchy4.',
        null,
        true,
        now() - interval '2 seconds'
    ),
    (
        'laptop-gaming-aliexpress',
        '¿Se Puede Construir una Laptop Gaming con Piezas de AliExpress?',
        'talleres',
        'https://www.youtube.com/watch?v=d-kc_vNFXno',
        'Canal: GameRig Español.',
        null,
        true,
        now() - interval '1 second'
    )
on conflict (slug) do update set
    title      = excluded.title,
    categoria  = excluded.categoria,
    video_url  = excluded.video_url,
    description = excluded.description,
    is_active  = true,
    published_at = excluded.published_at;
