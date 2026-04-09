# 贡献指南

感谢你对 PCB AI Inspector 的关注！欢迎提交 Issue 和 Pull Request。

## 提交方式

### 报告问题

通过 GitHub Issues 报告 bug 或功能请求，请包含：
- 清晰的描述
- 复现步骤
- 环境信息（操作系统、Python版本、GPU型号）

### 提交代码

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "Add xxx"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

## 开发环境

```bash
# 克隆并安装
git clone <your-fork-url>
cd pcb-ai-inspector
pip install -e ".[dev]"

# 格式化代码
make format

# 运行检查
make lint

# 运行测试
make test
```

## 代码规范

- 使用 black + isort 格式化代码
- 遵循 mypy 类型检查
- 提交前确保 `make lint` 和 `make test` 通过
- 公共 API 必须有类型注解和文档字符串

## 许可

本项目使用 AGPL-3.0 许可证，贡献代码即表示同意相同许可证。
