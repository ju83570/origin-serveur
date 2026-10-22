-- Seulement pour une base de test ayant déjà importé le schéma V2 initial.
-- Ne pas exécuter si le schema.sql de cette branche vient d'être importé.
ALTER TABLE users ADD COLUMN session_version BIGINT UNSIGNED NOT NULL DEFAULT 1 AFTER password_hash;
