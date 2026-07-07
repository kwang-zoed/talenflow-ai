-- MySQL dump 10.13  Distrib 8.0.12, for Win64 (x86_64)
--
-- Host: localhost    Database: dandelion_tribe
-- ------------------------------------------------------
-- Server version	8.0.12

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
 SET NAMES utf8 ;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `applications`
--

DROP TABLE IF EXISTS `applications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `applications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL COMMENT '求职者ID',
  `job_id` varchar(50) DEFAULT NULL COMMENT '如果是招聘职位',
  `task_id` int(11) DEFAULT NULL COMMENT '如果是实战任务',
  `resume_id` int(11) DEFAULT NULL COMMENT '投递时使用的简历ID',
  `cover_letter` text COMMENT '附言/自荐信',
  `status` varchar(20) DEFAULT 'pending' COMMENT '状态: pending(待查看), viewed(已查看), interviewed(面试中), rejected(已拒绝), accepted(已录用)',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `remark` text COMMENT '导师备注',
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_job` (`job_id`),
  KEY `idx_task` (`task_id`),
  CONSTRAINT `fk_app_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=47 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='投递记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `apply_tasks`
--

DROP TABLE IF EXISTS `apply_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `apply_tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `job_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `thread_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `celery_task_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stage` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `error` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `job_positions`
--

DROP TABLE IF EXISTS `job_positions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `job_positions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `job_id` varchar(50) DEFAULT NULL COMMENT '职位编号(外部来源或业务ID)',
  `title` varchar(150) NOT NULL COMMENT '职位名称',
  `company` varchar(100) NOT NULL COMMENT '公司名称',
  `location` varchar(100) DEFAULT NULL COMMENT '工作地点/城市',
  `salary` varchar(50) DEFAULT NULL COMMENT '薪资范围',
  `experience_requirement` varchar(50) DEFAULT NULL COMMENT '经验要求',
  `education_requirement` varchar(50) DEFAULT NULL COMMENT '学历要求',
  `required_skills` json DEFAULT NULL COMMENT '职位要求技能列表',
  `description` text COMMENT '职位描述全文(用于向量化)',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否有效',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `mentor_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `job_id` (`job_id`),
  KEY `idx_job_id` (`job_id`),
  KEY `idx_title` (`title`),
  KEY `fk_job_position_mentor` (`mentor_id`),
  CONSTRAINT `fk_job_position_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=55 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='职位信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `jobs`
--

DROP TABLE IF EXISTS `jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `jobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '职位ID',
  `title` varchar(100) NOT NULL COMMENT '职位名称',
  `company` varchar(100) NOT NULL COMMENT '公司名称',
  `description` text COMMENT '职位描述 (用于向量化)',
  `location` varchar(50) DEFAULT NULL COMMENT '工作地点',
  `salary_range` varchar(50) DEFAULT NULL COMMENT '薪资范围',
  `source_url` varchar(255) DEFAULT NULL COMMENT '原始链接',
  `vector_id` varchar(64) DEFAULT NULL COMMENT '关联向量数据库的ID',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  FULLTEXT KEY `ft_description` (`description`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='职位信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `notifications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `content` text,
  `type` varchar(50) DEFAULT 'system' COMMENT 'system, application_update, task_reminder',
  `is_read` tinyint(1) DEFAULT '0' COMMENT '是否已读',
  `link` varchar(500) DEFAULT NULL COMMENT '点击跳转链接',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_read` (`user_id`,`is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='消息通知表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resumes`
--

DROP TABLE IF EXISTS `resumes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `resumes` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` int(11) NOT NULL COMMENT '关联的用户ID',
  `name` varchar(50) DEFAULT NULL COMMENT '姓名',
  `phone` varchar(20) DEFAULT NULL COMMENT '电话',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `title` varchar(255) DEFAULT NULL COMMENT '求职意向/当前职位',
  `education` text COMMENT '教育经历 (JSON字符串或纯文本)',
  `work_experience` longtext COMMENT '工作经历 (使用LongText防止溢出)',
  `project_experience` longtext COMMENT '项目经历 (使用LongText)',
  `skills` json DEFAULT NULL COMMENT '技能列表 (推荐JSON格式，如 ["Python", "Java"])',
  `summary` text COMMENT '自我评价/个人总结',
  `source` varchar(255) DEFAULT NULL COMMENT '原文件路径/来源',
  `status` varchar(20) DEFAULT 'active' COMMENT '状态 (active, archived)',
  `parse_status` tinyint(4) DEFAULT '0' COMMENT '解析状态 (0:未解析, 1:成功, 2:失败)',
  `resume_language` varchar(10) DEFAULT 'zh' COMMENT '简历语言 (zh, en)',
  `target_job_id` varchar(100) DEFAULT NULL COMMENT '关联的职位ID',
  `vector_id` varchar(100) DEFAULT NULL COMMENT 'Faiss向量库中的ID',
  `is_default` tinyint(4) DEFAULT '0' COMMENT '是否默认简历',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `experience_years` int(11) DEFAULT NULL COMMENT '工作年限',
  `remark` varchar(500) DEFAULT NULL COMMENT '处理备注',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_target_job` (`target_job_id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='简历管理表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `skills`
--

DROP TABLE IF EXISTS `skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `skills` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '技能ID',
  `name` varchar(50) NOT NULL COMMENT '技能名称 (如: Python, Vue3)',
  `category` varchar(30) NOT NULL COMMENT '分类 (如: Language, Framework)',
  `parent_id` int(11) DEFAULT NULL COMMENT '父技能ID (用于构建层级关系)',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_category` (`category`),
  KEY `idx_parent_id` (`parent_id`),
  CONSTRAINT `fk_skill_parent` FOREIGN KEY (`parent_id`) REFERENCES `skills` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='技能字典表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_deliveries`
--

DROP TABLE IF EXISTS `task_deliveries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `task_deliveries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `delivery_url` varchar(255) DEFAULT NULL COMMENT '交付物链接 (GitHub等)',
  `comment` text COMMENT '用户备注',
  `status` varchar(20) DEFAULT 'submitted' COMMENT '状态: submitted, reviewed',
  `submitted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `review_comment` varchar(255) DEFAULT NULL COMMENT 'HR审核意见/驳回理由',
  `reviewer_id` int(11) DEFAULT NULL COMMENT '审核人(HR)ID',
  `resume_snapshot` json DEFAULT NULL COMMENT '投递时的简历快照(防止用户修改简历后数据不一致)',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `fk_td_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
  CONSTRAINT `fk_td_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务交付表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tasks`
--

DROP TABLE IF EXISTS `tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `title` varchar(150) NOT NULL COMMENT '任务标题',
  `description` text COMMENT '任务描述',
  `skills` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '所需技能 (逗号分隔或JSON)',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `category` varchar(20) DEFAULT NULL COMMENT '任务分类，如前端、后端、设计',
  `price` int(11) DEFAULT NULL COMMENT '任务赏金（单位：元）',
  `duration` varchar(20) DEFAULT NULL COMMENT '预计工期，如 3天、1周',
  `difficulty` varchar(50) DEFAULT '中等',
  `taken_by` int(11) DEFAULT NULL COMMENT '接单人ID',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `status` tinyint(4) DEFAULT '1' COMMENT '任务状态：0-待审核, 1-进行中, 2-已暂停, 3-已完成, 4-已驳回',
  `mentor_id` int(11) NOT NULL DEFAULT '0' COMMENT '发布者ID',
  PRIMARY KEY (`id`),
  KEY `idx_mentor_id` (`mentor_id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='实战任务表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `transactions`
--

DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `transactions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `wallet_id` int(11) NOT NULL,
  `amount` decimal(10,2) NOT NULL COMMENT '变动金额',
  `type` varchar(20) NOT NULL COMMENT '类型: income(收入), withdraw(提现), fee(手续费)',
  `related_id` int(11) DEFAULT NULL COMMENT '关联的任务ID或提现申请ID',
  `balance_after` decimal(10,2) NOT NULL COMMENT '变动后余额',
  `status` varchar(20) DEFAULT 'completed' COMMENT '状态: completed, processing, failed',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_time` (`user_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易流水表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_profiles`
--

DROP TABLE IF EXISTS `user_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `user_profiles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL COMMENT '业务用户ID',
  `name` varchar(100) DEFAULT NULL COMMENT '用户姓名',
  `skills` json DEFAULT NULL COMMENT '用户掌握的技能列表',
  `profile_summary` text COMMENT '用户画像文本摘要(用于向量化)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `expected_position` varchar(100) DEFAULT NULL COMMENT '期望职位，如：Java后端工程师',
  `expected_city` varchar(50) DEFAULT NULL COMMENT '期望工作城市',
  `expected_industry` varchar(50) DEFAULT NULL COMMENT '期望行业，如：互联网, 金融',
  `min_salary` int(11) DEFAULT NULL COMMENT '期望最低薪资',
  `job_type` varchar(20) DEFAULT NULL COMMENT '工作性质：全职, 兼职, 实习',
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户画像表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_resume_cache`
--

DROP TABLE IF EXISTS `user_resume_cache`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `user_resume_cache` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `job_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `optimized_resume_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_job` (`user_id`,`job_id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `email` varchar(100) NOT NULL COMMENT '邮箱 (登录账号)',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '密码哈希值',
  `role` tinyint(1) DEFAULT '0' COMMENT '角色: candidate, mentor, admin',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `full_name` varchar(50) DEFAULT NULL COMMENT '用户昵称/真实姓名',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活: 1正常, 0封禁',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户基础信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wallets`
--

DROP TABLE IF EXISTS `wallets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
 SET character_set_client = utf8mb4 ;
CREATE TABLE `wallets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL COMMENT '用户ID',
  `balance` decimal(10,2) DEFAULT '0.00' COMMENT '余额',
  `freeze_amount` decimal(10,2) DEFAULT '0.00' COMMENT '冻结金额（如有提现中）',
  `total_earnings` decimal(10,2) DEFAULT '0.00' COMMENT '累计收益',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user` (`user_id`),
  CONSTRAINT `fk_wallet_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户钱包表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-02 15:26:33
