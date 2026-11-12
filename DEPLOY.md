# Cloudflare Pages 云端存档

现有 Git 部署使用项目根目录作为 Pages 根目录，`functions/api/` 提供同源 API。静态页面无需构建。

1. 在 Cloudflare 创建 D1 数据库。
2. 初始化数据库。把命令中的数据库名换成实际名称，并在项目根目录运行：

   ```sh
   npx wrangler d1 execute <数据库名> --remote --file=migrations/0001_accounts.sql
   ```

3. 在 Pages 项目设置的 Bindings 中添加 D1 绑定，变量名必须是 `DB`。给生产环境和使用云端存档的预览环境分别绑定各自的数据库，并分别初始化。
4. 提交并推送到 Pages 的 Git 部署分支，确认构建启用了 Pages Functions。变更绑定后重新部署。
5. 在部署后的 HTTPS 网站中打开「账号」，用两个测试账号验证注册、退出、重新登录、云端保存和账号间隔离。

已有浏览器存档可在「我的角色 → 本机角色」中逐张点击「复制到云端」。云端角色支持独立编辑和删除，每张云端角色的 JSON 请求上限为 1,800,000 字节。
