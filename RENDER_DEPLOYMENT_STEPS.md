# Render部署检查具体步骤

## 1. 登录Render控制台

### 访问Render网站
1. 打开浏览器，访问：https://render.com
2. 点击右上角的 "Log In" 按钮
3. 使用你的GitHub账户登录（如果waypal.ai项目是通过GitHub部署的）

## 2. 找到waypal.ai项目

### 在Dashboard中查找
1. 登录后，你会看到Render Dashboard
2. 在 "Services" 或 "Web Services" 部分查找名为 "waypal" 或 "waypal-ai" 的服务
3. 如果找不到，检查是否有其他相关名称的服务

### 可能的服务名称
- `waypal`
- `waypal-ai` 
- `flight-selector`
- `gg-bot`
- 或其他自定义名称

## 3. 检查部署状态

### 点击进入服务详情
1. 找到waypal相关服务后，点击服务名称
2. 进入服务详情页面

### 查看部署信息
在服务详情页面，你会看到：

**部署历史 (Deploy History)**
- 查看最新的部署时间
- 检查部署状态：✅ Success / ❌ Failed / ⏳ Building
- 查看部署的Git提交哈希

**当前状态**
- 服务状态：Live / Building / Failed
- 最后部署时间
- 使用的分支（通常是 `main`）

## 4. 检查最新部署

### 查看部署详情
1. 点击最新的部署记录
2. 查看部署日志 (Build Logs)
3. 检查是否有错误信息

### 确认Git提交
- 查看部署使用的Git提交哈希
- 确认是否使用了我们最新的提交：`7a15bfd` (消息格式修复)
- 确认是否使用了地图修复提交：`43b07e9`

## 5. 手动触发部署（如果需要）

### 如果自动部署未触发
1. 在服务详情页面，找到 "Manual Deploy" 按钮
2. 点击 "Deploy latest commit" 或类似选项
3. 等待部署完成

### 如果部署失败
1. 查看构建日志中的错误信息
2. 常见问题：
   - 依赖安装失败
   - 环境变量缺失
   - 构建命令错误
   - 端口配置问题

## 6. 验证部署结果

### 测试网站功能
1. 访问 https://waypal.ai
2. 检查网站是否正常加载
3. 测试航班查询功能

### 检查修复效果
1. **地图修复验证**：
   - 发送航班查询给机器人
   - 点击生成的web链接
   - 检查地图是否显示正确路线（不再是东京）

2. **手机端修复验证**：
   - 在手机上打开web链接
   - 检查布局是否美观
   - 确认按钮和文字是否易于操作

## 7. 常见问题排查

### 如果找不到服务
1. 检查是否使用了不同的Render账户
2. 确认项目是否部署在Render上
3. 检查是否有其他部署平台（Heroku、Railway等）

### 如果部署失败
1. **检查构建日志**：
   ```
   Build failed: Module not found
   Build failed: Environment variables missing
   Build failed: Port configuration error
   ```

2. **检查环境变量**：
   - 确保所有必要的环境变量已设置
   - 检查API密钥是否有效

3. **检查依赖**：
   - 确认 `requirements.txt` 文件正确
   - 检查Python版本兼容性

### 如果网站无法访问
1. 检查服务状态是否为 "Live"
2. 确认域名配置正确
3. 检查是否有DNS问题

## 8. 联系支持（如果需要）

### 如果遇到技术问题
1. 查看Render文档：https://render.com/docs
2. 联系Render支持：https://render.com/support
3. 检查Render状态页面：https://status.render.com

## 9. 部署成功后的验证清单

- [ ] 服务状态显示为 "Live"
- [ ] 最新部署时间显示为今天
- [ ] 部署使用的Git提交包含我们的修复
- [ ] https://waypal.ai 可以正常访问
- [ ] 地图显示正确的航班路线
- [ ] 手机端布局正常
- [ ] 机器人回复格式简洁无emoji

## 10. 下一步行动

如果部署成功：
1. 测试完整的航班查询流程
2. 验证所有修复功能
3. 确认用户体验改善

如果部署失败：
1. 根据错误日志进行修复
2. 重新触发部署
3. 必要时联系技术支持

