# 部署到 waypal.ai 的说明

## 部署步骤

### 1. 准备文件
确保以下文件已准备好：
- `flight_selector_production.py` - 生产环境Web服务器
- `templates/` - HTML模板文件夹
- `static/` - CSS/JS静态文件文件夹
- `requirements_web_production.txt` - Python依赖
- `Procfile` - 部署配置

### 2. 部署选项

#### 选项A: 使用Heroku部署
```bash
# 安装Heroku CLI
# 登录Heroku
heroku login

# 创建应用
heroku create waypal-flight-selector

# 设置环境变量
heroku config:set DEBUG=False

# 部署
git add .
git commit -m "Deploy flight selector to waypal.ai"
git push heroku main
```

#### 选项B: 使用Railway部署
```bash
# 安装Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 部署
railway up
```

#### 选项C: 使用Render部署
1. 连接GitHub仓库到Render
2. 选择Python环境
3. 设置构建命令: `pip install -r requirements_web_production.txt`
4. 设置启动命令: `gunicorn flight_selector_production:app`

### 3. 域名配置
将waypal.ai域名指向部署的服务器：
- 在DNS设置中添加CNAME记录
- 指向部署平台的域名

### 4. 测试部署
部署完成后，测试以下URL：
- https://waypal.ai/ - 主页面
- https://waypal.ai/api/flights - API端点

### 5. 更新机器人
机器人代码已更新为使用 https://waypal.ai 而不是 localhost:5001

## 文件结构
```
waypal-flight-selector/
├── flight_selector_production.py
├── templates/
│   ├── flight_selector.html
│   └── flight_options.html
├── static/
│   ├── css/
│   │   └── flight_selector.css
│   └── js/
│       └── flight_selector.js
├── requirements_web_production.txt
├── Procfile
└── DEPLOYMENT.md
```

