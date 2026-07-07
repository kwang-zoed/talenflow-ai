-- 求职者所在地 + 岗位坐标（距离推荐）
-- 执行: mysql -u root -p dandelion_tribe < scripts/migrations/add_location_coords.sql

ALTER TABLE `user_profiles`
  ADD COLUMN `residence_city` VARCHAR(100) DEFAULT NULL COMMENT '常住省市区' AFTER `expected_city`,
  ADD COLUMN `residence_address` VARCHAR(255) DEFAULT NULL COMMENT '详细住址' AFTER `residence_city`,
  ADD COLUMN `latitude` DECIMAL(10,7) DEFAULT NULL AFTER `residence_address`,
  ADD COLUMN `longitude` DECIMAL(10,7) DEFAULT NULL AFTER `latitude`,
  ADD COLUMN `geocoded_at` DATETIME DEFAULT NULL AFTER `longitude`;

ALTER TABLE `resumes`
  ADD COLUMN `residence_city` VARCHAR(100) DEFAULT NULL COMMENT '常住省市区' AFTER `target_job_id`,
  ADD COLUMN `residence_address` VARCHAR(255) DEFAULT NULL COMMENT '详细住址' AFTER `residence_city`,
  ADD COLUMN `latitude` DECIMAL(10,7) DEFAULT NULL AFTER `residence_address`,
  ADD COLUMN `longitude` DECIMAL(10,7) DEFAULT NULL AFTER `latitude`,
  ADD COLUMN `use_profile_location` TINYINT NOT NULL DEFAULT 1 COMMENT '1=继承用户默认所在地' AFTER `longitude`;

ALTER TABLE `job_positions`
  ADD COLUMN `work_address` VARCHAR(255) DEFAULT NULL COMMENT '详细工作地址' AFTER `location`,
  ADD COLUMN `latitude` DECIMAL(10,7) DEFAULT NULL AFTER `work_address`,
  ADD COLUMN `longitude` DECIMAL(10,7) DEFAULT NULL AFTER `latitude`,
  ADD COLUMN `geocoded_at` DATETIME DEFAULT NULL AFTER `longitude`;
