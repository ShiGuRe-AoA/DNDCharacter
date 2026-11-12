# Cloudflare Workers 云端存档

Workers Builds 的根目录使用仓库根目录，部署命令继续使用 `npx wrangler deploy`。Wrangler 根据 `wrangler.jsonc` 部署静态页面和同源 `/api/*` 接口。`.assetsignore` 限定公开文件，数据库迁移和 Worker 源码不会作为静态文件上传。

## 配置 D1

- **已有 D1 数据库**：如果之前已经创建了角色卡数据库，请在首次 Workers 部署前编辑 `wrangler.jsonc`，为 `DB` 添加该数据库的 `database_name` 和 `database_id`，以继续使用同一份数据。
- **首次使用 D1**：Wrangler 4.45.0 及以后版本可以在部署时自动为 `DB` 创建并绑定数据库。如果构建凭据缺少 D1 创建权限，可先在 Cloudflare 控制台创建数据库，再按上一步配置名称和 ID。

在 Cloudflare 控制台找到 Worker 绑定的 D1 数据库，并在 D1 Console 执行 `migrations/0001_accounts.sql`。已有这份表结构的数据库无需重新执行。也可以在仓库根目录用 Wrangler 对目标数据库执行初始化：

```sh
npx wrangler d1 execute "<实际数据库名或 UUID>" --remote --file=migrations/0001_accounts.sql
```

## 验证

提交并推送到 Workers Builds 的部署分支。部署和 D1 初始化完成后，访问原网站，打开「账号」，验证注册、退出、重新登录、云端保存和账号间隔离。已有浏览器存档可在「我的角色 → 本机角色」中逐张点击「复制到云端」。

## 初始化测试法术库

`RULES_DB` 是独立的 D1 绑定，和存放账号及角色卡的 `DB` 对应不同数据库。Git 部署成功后，在 Worker 的 **Bindings** 中确认 `RULES_DB` 指向的数据库。如果需要手动指定数据库，在 `wrangler.jsonc` 为该绑定填写对应的 `database_name` 和 `database_id`，再推送部署。

在该数据库的 D1 Console 中执行 `rules-migrations/0001_test_spells.sql` 一次。也可在仓库根目录使用 Wrangler：

```sh
npx wrangler d1 execute "<RULES_DB 实际数据库名或 UUID>" --remote --file=rules-migrations/0001_test_spells.sql
```

在角色卡点「添加法术」，输入「火球」或 `fireball`。应看到 2014 和 2024 两条候选，点击其中一条会填写法术表单。测试库含 24 条记录，法术描述为简短摘要。
