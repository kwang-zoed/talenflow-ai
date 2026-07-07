-- TalentFlow RAG 评测专用职位种子（ID 9001-9013）
-- 用法（MySQL）:
--   mysql -u root -p dandelion_tribe < scripts/eval/datasets/seed_eval_jobs.sql
-- 或通过 python scripts/eval/cli.py import-jobs 自动导入并写入 FAISS

DELETE FROM job_positions WHERE job_id LIKE 'eval-%';

INSERT INTO job_positions
  (id, job_id, title, company, location, salary, experience_requirement, education_requirement, required_skills, description, is_active, mentor_id)
VALUES
(9001, 'eval-9001', 'Python后端开发工程师', '深圳云智科技', '深圳',
 '20K-35K', '3-5年', '本科',
 JSON_ARRAY('Python', 'Django', 'FastAPI', 'MySQL', 'Redis'),
 '负责公司核心业务后端 API 开发，使用 Python、Django/FastAPI 构建高并发服务，参与微服务拆分与性能优化。',
 1, NULL),

(9002, 'eval-9002', 'Java后端开发工程师', '深圳科创软件', '深圳',
 '18K-30K', '3-5年', '本科',
 JSON_ARRAY('Java', 'Spring Boot', 'MySQL', 'Redis'),
 '参与电商平台后端开发，使用 Java Spring Boot 构建 RESTful 服务，负责订单与支付模块。',
 1, NULL),

(9003, 'eval-9003', 'Go微服务开发工程师', '北京互联科技', '北京',
 '25K-40K', '3-5年', '本科',
 JSON_ARRAY('Go', 'gRPC', 'Kubernetes', '微服务'),
 '负责 Go 语言微服务开发，使用 gRPC 通信，部署于 Kubernetes 集群。',
 1, NULL),

(9004, 'eval-9004', 'Python数据分析师', '上海数联科技', '上海',
 '15K-25K', '1-3年', '本科',
 JSON_ARRAY('Python', 'Pandas', 'SQL', '数据可视化'),
 '使用 Python 进行数据清洗、分析与可视化，支持业务决策与报表建设。',
 1, NULL),

(9005, 'eval-9005', 'Java开发工程师（应届生）', '杭州电商科技', '杭州',
 '10K-15K', '应届生', '本科',
 JSON_ARRAY('Java', 'MySQL', 'Spring'),
 '面向应届毕业生的 Java 开发岗位，参与业务系统开发与单元测试，有导师带教。',
 1, NULL),

(9006, 'eval-9006', '资深Python架构师', '深圳云智科技', '深圳',
 '40K-60K', '8年以上', '本科',
 JSON_ARRAY('Python', '微服务', '架构设计', '分布式'),
 '主导 Python 技术栈架构设计，负责核心系统技术选型、性能治理与团队技术指导。',
 1, NULL),

(9007, 'eval-9007', '全栈工程师（Python+Vue）', '远程工坊科技', '远程',
 '22K-35K', '3-5年', '本科',
 JSON_ARRAY('Python', 'Vue', 'FastAPI', '全栈'),
 '远程全职，负责 Python 后端与 Vue 前端全栈开发，构建 SaaS 产品。',
 1, NULL),

(9008, 'eval-9008', '前端React开发工程师', '深圳前端科技', '深圳',
 '18K-28K', '3-5年', '本科',
 JSON_ARRAY('React', 'TypeScript', '前端工程化'),
 '负责 React + TypeScript 前端开发，参与组件库建设与性能优化。',
 1, NULL),

(9009, 'eval-9009', 'DevOps工程师', '远程云原生科技', '远程',
 '25K-40K', '5年以上', '本科',
 JSON_ARRAY('Docker', 'Kubernetes', 'CI/CD', 'Go'),
 '远程岗位，负责容器化部署、CI/CD 流水线与云原生基础设施运维。',
 1, NULL),

(9010, 'eval-9010', 'Python后端工程师', '东莞智造科技', '东莞',
 '12K-20K', '1-3年', '大专',
 JSON_ARRAY('Python', 'Flask', 'MySQL'),
 '参与制造业信息化系统后端开发，使用 Python Flask 构建内部管理系统。',
 1, NULL),

(9011, 'eval-9011', '高级Java架构师', '上海金融科技', '上海',
 '45K-70K', '8年以上', '本科',
 JSON_ARRAY('Java', '分布式', '架构设计', '高并发'),
 '负责金融核心系统架构设计，主导 Java 分布式系统建设与稳定性治理。',
 1, NULL),

(9012, 'eval-9012', '区块链Go开发工程师', '北京链科科技', '北京',
 '30K-50K', '3-5年', '本科',
 JSON_ARRAY('Go', '区块链', '智能合约'),
 '使用 Go 开发区块链底层与智能合约相关服务。',
 1, NULL),

(9013, 'eval-9013', 'Go后端工程师（远程）', '远程极客科技', '远程',
 '22K-38K', '3-5年', '本科',
 JSON_ARRAY('Go', '微服务', 'gRPC', '远程协作'),
 '远程全职 Go 后端开发，构建高可用微服务与 API 网关。',
 1, NULL);
