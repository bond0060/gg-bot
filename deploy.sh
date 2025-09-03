#!/bin/bash

echo "🚀 准备部署到 waypal.ai..."

# 检查必要文件
echo "📋 检查部署文件..."
required_files=(
    "flight_selector_production.py"
    "templates/flight_selector.html"
    "templates/flight_options.html"
    "static/css/flight_selector.css"
    "static/js/flight_selector.js"
    "requirements_web_production.txt"
    "Procfile"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少文件: $file"
        exit 1
    fi
done

echo "✅ 所有必要文件都存在"

# 创建部署目录
echo "📁 创建部署目录..."
mkdir -p waypal-deployment
cd waypal-deployment

# 复制文件
echo "📋 复制文件到部署目录..."
cp ../flight_selector_production.py .
cp -r ../templates .
cp -r ../static .
cp ../requirements_web_production.txt requirements.txt
cp ../Procfile .

echo "✅ 文件复制完成"

echo ""
echo "🎯 部署选项："
echo "1. Heroku: heroku create waypal-flight-selector && git push heroku main"
echo "2. Railway: railway init && railway up"
echo "3. Render: 连接GitHub仓库并设置构建命令"
echo ""
echo "📝 部署完成后，确保将waypal.ai域名指向部署的服务器"
echo "🔗 测试URL: https://waypal.ai/"
echo ""
echo "✅ 部署准备完成！"

