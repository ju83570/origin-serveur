-- Execute with phpMyAdmin on a NEW dedicated MySQL database (utf8mb4).
CREATE TABLE IF NOT EXISTS users (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 email VARCHAR(190) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 session_version BIGINT UNSIGNED NOT NULL DEFAULT 1,
 verified_at DATETIME NULL,
 stripe_customer_id VARCHAR(100) UNIQUE NULL,
 privacy_version VARCHAR(30) NOT NULL,
 privacy_accepted_at DATETIME NOT NULL,
 created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS email_tokens (
 user_id BIGINT UNSIGNED PRIMARY KEY,
 token_hash CHAR(64) NOT NULL UNIQUE,
 expires_at DATETIME NOT NULL,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- A distinct one-time token, not the password, is emailed for password recovery.
CREATE TABLE IF NOT EXISTS password_resets (
 user_id BIGINT UNSIGNED PRIMARY KEY,
 token_hash CHAR(64) NOT NULL UNIQUE,
 expires_at DATETIME NOT NULL,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS user_state (
 user_id BIGINT UNSIGNED PRIMARY KEY,
 sealed_payload MEDIUMTEXT NOT NULL,
 revision BIGINT UNSIGNED NOT NULL DEFAULT 1,
 updated_at DATETIME NOT NULL,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
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
CREATE TABLE IF NOT EXISTS subscriptions (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 order_id CHAR(36) NULL,
 stripe_subscription_id VARCHAR(100) NOT NULL UNIQUE,
 plan VARCHAR(40) NOT NULL,
 status VARCHAR(40) NOT NULL,
 current_period_end DATETIME NULL,
 updated_at DATETIME NOT NULL,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY (order_id) REFERENCES orders(order_id),
 INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS purchases (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 order_id CHAR(36) NULL,
 product VARCHAR(40) NOT NULL DEFAULT 'unverified',
 stripe_session_id VARCHAR(120) NOT NULL UNIQUE,
 status VARCHAR(20) NOT NULL,
 created_at DATETIME NOT NULL,
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS stripe_events (
 event_id VARCHAR(150) PRIMARY KEY,
 event_type VARCHAR(100) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'received',
 processed_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS rate_limit_counters (
 bucket VARCHAR(25) NOT NULL,
 fingerprint CHAR(64) NOT NULL,
 window_start BIGINT UNSIGNED NOT NULL,
 attempts BIGINT UNSIGNED NOT NULL,
 PRIMARY KEY(bucket,fingerprint,window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS rate_limits (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 bucket VARCHAR(25) NOT NULL,
 fingerprint CHAR(64) NOT NULL,
 created_at DATETIME NOT NULL,
 INDEX idx_limits (bucket, fingerprint, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migration 004, additive. Sur copie de préproduction seulement avant validation.
-- Les anciens orders/purchases/subscriptions sont conservés. Aucun droit ancien
-- n'est inventé : rapprochement Stripe explicite avant import dans ce registre.
CREATE TABLE IF NOT EXISTS order_items (
 order_item_id CHAR(36) PRIMARY KEY,
 order_id CHAR(36) NOT NULL,
 environment VARCHAR(20) NOT NULL,
 revision INT UNSIGNED NOT NULL DEFAULT 1,
 position INT UNSIGNED NOT NULL DEFAULT 1,
 sku VARCHAR(40) NOT NULL,
 price_id VARCHAR(100) NOT NULL,
 unit_amount BIGINT UNSIGNED NOT NULL,
 quantity INT UNSIGNED NOT NULL,
 currency CHAR(3) NOT NULL,
 UNIQUE KEY item_revision (environment,order_id,position,revision),
 FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS payment_attempts (
 attempt_id CHAR(36) PRIMARY KEY,
 order_id CHAR(36) NOT NULL,
 environment VARCHAR(20) NOT NULL,
 idempotency_key VARCHAR(100) NOT NULL,
 stripe_customer_id VARCHAR(100) NOT NULL,
 stripe_session_id VARCHAR(120) NULL,
 stripe_payment_intent_id VARCHAR(100) NULL,
 status VARCHAR(30) NOT NULL DEFAULT 'pending',
 verified_at DATETIME NULL,
 refunded_amount BIGINT UNSIGNED NOT NULL DEFAULT 0,
 lease_token CHAR(64) NULL,
 lease_until DATETIME NULL,
 created_at DATETIME NOT NULL,
 UNIQUE KEY checkout_once (environment,order_id),
 UNIQUE KEY stripe_session (environment,stripe_session_id),
 UNIQUE KEY stripe_intent (environment,stripe_payment_intent_id),
 UNIQUE KEY attempt_idempotency (environment,idempotency_key),
 FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS customer_bindings (
 user_id BIGINT UNSIGNED NOT NULL,
 environment VARCHAR(20) NOT NULL,
 stripe_customer_id VARCHAR(100) NULL,
 idempotency_key VARCHAR(100) NOT NULL,
 lease_token CHAR(64) NULL,
 lease_until DATETIME NULL,
 PRIMARY KEY(user_id,environment),
 UNIQUE KEY customer_binding (environment,stripe_customer_id),
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS entitlements (
 entitlement_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 order_item_id CHAR(36) NOT NULL,
 environment VARCHAR(20) NOT NULL,
 capability VARCHAR(60) NOT NULL,
 status VARCHAR(20) NOT NULL,
 valid_until DATETIME NULL,
 updated_at DATETIME NOT NULL,
 UNIQUE KEY item_capability (environment,order_item_id,capability),
 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY (order_item_id) REFERENCES order_items(order_item_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS stripe_inbox (
 environment VARCHAR(20) NOT NULL,
 event_id VARCHAR(150) NOT NULL,
 event_type VARCHAR(100) NOT NULL,
 event_created BIGINT UNSIGNED NOT NULL,
 payload_hash CHAR(64) NOT NULL,
 sealed_payload MEDIUMTEXT NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'received',
 attempts INT UNSIGNED NOT NULL DEFAULT 0,
 lease_token CHAR(64) NULL,
 lease_until DATETIME NULL,
 next_attempt_at DATETIME NOT NULL,
 last_error VARCHAR(80) NULL,
 received_at DATETIME NOT NULL,
 processed_at DATETIME NULL,
 PRIMARY KEY(environment,event_id),
 INDEX pending_events (environment,status,next_attempt_at,received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS payment_disputes (
 environment VARCHAR(20) NOT NULL,
 dispute_id VARCHAR(100) NOT NULL,
 attempt_id CHAR(36) NOT NULL,
 status VARCHAR(40) NOT NULL,
 updated_at DATETIME NOT NULL,
 PRIMARY KEY(environment,dispute_id),
 FOREIGN KEY (attempt_id) REFERENCES payment_attempts(attempt_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS jobs (
 job_id CHAR(36) PRIMARY KEY,
 order_item_id CHAR(36) NOT NULL,
 revision INT UNSIGNED NOT NULL,
 environment VARCHAR(20) NOT NULL,
 state VARCHAR(30) NOT NULL DEFAULT 'queued',
 created_at DATETIME NOT NULL,
 UNIQUE KEY fulfillment_once (order_item_id,revision,environment),
 FOREIGN KEY (order_item_id) REFERENCES order_items(order_item_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS outbox (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 environment VARCHAR(20) NOT NULL,
 dedupe_key CHAR(64) NOT NULL,
 topic VARCHAR(80) NOT NULL,
 aggregate_id CHAR(36) NOT NULL,
 payload TEXT NOT NULL,
 state VARCHAR(20) NOT NULL DEFAULT 'pending',
 created_at DATETIME NOT NULL,
 UNIQUE KEY effect_once (environment,dedupe_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payment_adjustments (
 environment VARCHAR(20) NOT NULL,
 source_id VARCHAR(100) NOT NULL,
 order_id CHAR(36) NOT NULL,
 attempt_id CHAR(36) NOT NULL,
 payment_intent_id VARCHAR(100) NOT NULL,
 invoice_id VARCHAR(100) NULL,
 amount BIGINT UNSIGNED NOT NULL,
 refunded_amount BIGINT UNSIGNED NOT NULL,
 currency CHAR(3) NOT NULL,
 status VARCHAR(40) NOT NULL,
 updated_at DATETIME NOT NULL,
 PRIMARY KEY(environment,source_id),
 FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE RESTRICT,
 FOREIGN KEY (attempt_id) REFERENCES payment_attempts(attempt_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
