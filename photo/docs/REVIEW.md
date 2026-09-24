# 状态记录

测试确认：主路径无阻塞问题。方案冻结，不回改架构。

已完成：
- Phase 1–6 小程序主路径（构图、广场、发布、点赞、个人中心）。
- 发布状态机 `pending → published/rejected`，用户级发布频控入库，推荐支持地理邻近。
- 已接入正式环境：AppID `wx8f423547346142e3`，云环境 `cloud1-d0gvm9vln716a26f5`。`config.js` 填写后关闭 Mock。
- 已增加 `initDatabase` 云函数，用于创建 `users` / `photos` / `likes` / `audit_logs`。

操作侧仍需在开发者工具完成：上传全部云函数（含 `mediaCheckCallback`）、运行 `initDatabase`、按 `database/indexes.json` 建索引，并将多媒体检测回调绑定到 `mediaCheckCallback`。

`mediaCheckAsync` 原图异步复核已落地：同步通过即可上架；异步未通过则下架并删除云文件。
