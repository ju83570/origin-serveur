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
