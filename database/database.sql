-- ============================================================
-- News App — clean schema (no seed data)
-- All news content is populated exclusively by the scraper.
-- ============================================================

CREATE DATABASE IF NOT EXISTS news_app DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE news_app;

CREATE TABLE IF NOT EXISTS `user` (
  `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username`   VARCHAR(50)  NOT NULL,
  `password`   VARCHAR(255) NOT NULL,
  `nickname`   VARCHAR(50)  NULL DEFAULT NULL,
  `avatar`     VARCHAR(255) NULL DEFAULT NULL,
  `gender`     ENUM('male','female','unknown') NULL DEFAULT 'unknown',
  `bio`        VARCHAR(500) NULL DEFAULT NULL,
  `phone`      VARCHAR(20)  NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `username_UNIQUE` (`username`),
  UNIQUE INDEX `phone_UNIQUE`    (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `user_token` (
  `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`    INT UNSIGNED NOT NULL,
  `token`      VARCHAR(64)  NOT NULL,   -- stores SHA-256 hash of the raw bearer token
  `expires_at` TIMESTAMP    NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `token_UNIQUE`          (`token`),
  INDEX        `fk_user_token_user_idx`(`user_id`),
  CONSTRAINT `fk_user_token_user`
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `news_category` (
  `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`       VARCHAR(50)  NOT NULL,
  `sort_order` INT NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `name_UNIQUE` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `news` (
  `id`           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `title`        VARCHAR(255) NOT NULL,
  `description`  VARCHAR(500) NULL DEFAULT NULL,
  `content`      TEXT         NOT NULL,
  `image`        VARCHAR(500) NULL DEFAULT NULL,   -- enlarged to 500 to accommodate long CDN URLs
  `author`       VARCHAR(100) NULL DEFAULT NULL,
  `category_id`  INT UNSIGNED NOT NULL,
  `views`        INT UNSIGNED NOT NULL DEFAULT 0,
  `embedding`    MEDIUMTEXT   NULL DEFAULT NULL COMMENT 'JSON float array from text-embedding-3-small (1536 dims)',
  `publish_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at`   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `fk_news_category_idx` (`category_id`),
  INDEX `idx_publish_time`     (`publish_time` DESC),
  CONSTRAINT `fk_news_category`
    FOREIGN KEY (`category_id`) REFERENCES `news_category`(`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `favorite` (
  `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`    INT UNSIGNED NOT NULL,
  `news_id`    INT UNSIGNED NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uniq_user_news`      (`user_id`, `news_id`),
  INDEX        `fk_favorite_user_idx`(`user_id`),
  INDEX        `fk_favorite_news_idx`(`news_id`),
  CONSTRAINT `fk_favorite_user`
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_favorite_news`
    FOREIGN KEY (`news_id`) REFERENCES `news`(`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `history` (
  `id`        INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`   INT UNSIGNED NOT NULL,
  `news_id`   INT UNSIGNED NOT NULL,
  `view_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `fk_history_user_idx`(`user_id`),
  INDEX `fk_history_news_idx`(`news_id`),
  INDEX `idx_view_time`       (`view_time` DESC),
  CONSTRAINT `fk_history_user`
    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_history_news`
    FOREIGN KEY (`news_id`) REFERENCES `news`(`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
