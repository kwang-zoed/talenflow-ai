# E2E 手动验收清单（E2E 通过后可删除）

## T4 路由 + API
- [ ] HR 访问 `/hr/jobs/1/recommend` 正常渲染
- [ ] 非 HR 被重定向
- [ ] `hrRecommend.js` submit 返回 task_id

## T5 页面
- [ ] 页头显示职位信息
- [ ] 自动 submit + loading
- [ ] 推荐列表展示姓名/匹配度/技能
- [ ] 刷新重新推荐
- [ ] 10 分钟缓存
- [ ] 空状态 el-empty
- [ ] 查看简历弹窗
- [ ] 列表脱敏 phone/email
- [ ] GlobalTaskProgress resume_recommend

## T6 入口
- [ ] HrJobs「智能推荐简历」跳转
- [ ] 进度条点击回跳 recommend 页

## E1-E6 全流程
- [ ] HR 登录 → 岗位管理 → 智能推荐 → 查看详情
