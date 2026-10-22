-- Migration 003 : appliquer UNE SEULE FOIS sur copie de base, sauvegarde vérifiée.
-- Ne pas exécuter automatiquement en production. Conserver app_key et anciennes clés.

CREATE TABLE IF NOT EXISTS user_state_history (
 user_id BIGINT UNSIGNED NOT NULL,
 revision BIGINT UNSIGNED NOT NULL,
 sealed_payload MEDIUMTEXT NOT NULL,
 updated_at DATETIME NOT NULL,
 PRIMARY KEY(user_id,revision),
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS orders (
 order_id CHAR(36) PRIMARY KEY,
 user_id BIGINT UNSIGNED NULL,
 product VARCHAR(40) NOT NULL,
 environment VARCHAR(20) NOT NULL,
 price_id VARCHAR(100) NOT NULL,
 amount BIGINT UNSIGNED NOT NULL,
 currency CHAR(3) NOT NULL,
 status VARCHAR(30) NOT NULL DEFAULT 'pending',
 stripe_customer_id VARCHAR(100) NOT NULL,
 stripe_session_id VARCHAR(120) UNIQUE NULL,
 stripe_subscription_id VARCHAR(100) UNIQUE NULL,
 stripe_payment_intent_id VARCHAR(100) UNIQUE NULL,
 created_at DATETIME NOT NULL,
 expires_at DATETIME NOT NULL,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rate_limit_counters (
 bucket VARCHAR(25) NOT NULL,
 fingerprint CHAR(64) NOT NULL,
 window_start BIGINT UNSIGNED NOT NULL,
 attempts BIGINT UNSIGNED NOT NULL,
 PRIMARY KEY(bucket,fingerprint,window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE user_state ADD COLUMN revision BIGINT UNSIGNED NOT NULL DEFAULT 1;
ALTER TABLE subscriptions ADD COLUMN order_id CHAR(36) NULL,
 ADD CONSTRAINT fk_subscription_order FOREIGN KEY (order_id) REFERENCES orders(order_id);
ALTER TABLE purchases ADD COLUMN order_id CHAR(36) NULL,
 ADD COLUMN product VARCHAR(40) NOT NULL DEFAULT 'unverified',
 ADD CONSTRAINT fk_purchase_order FOREIGN KEY (order_id) REFERENCES orders(order_id);
-- Les événements déjà consommés ne doivent pas être réappliqués.
ALTER TABLE stripe_events ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'processed';
-- Les achats/abonnements historiques sont conservés, sans droits présumés.
-- Réconcilier chaque ligne avec Stripe et une commande avant attribution.
