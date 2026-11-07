# 起源心金 4.03 存档编辑器

这是一个单 HTML 可直接运行的《起源心金 4.03》存档编辑器。

## 使用方式

直接打开根目录的 `originhgss-save-editor.html`，选择游戏存档文件即可使用。应用在浏览器本地读取和修改存档，不需要安装运行环境。

## 文件结构

- `originhgss-save-editor.html`：可交付的单文件应用，运行所需数据已内嵌。
- `data/originhgss-4.03-data.js`：4.03 数据源备份，供后续维护和重新生成内嵌数据使用。
- `docs/feature-gap-report.md`：功能差异与后续规划记录。

## GitHub Pages

在仓库设置中启用 GitHub Pages，并选择 `main` 分支的根目录作为发布目录，即可通过网页访问这个编辑器。

ROM 和存档文件不应提交到仓库。应用运行所需的静态数据已经包含在 HTML 中。
