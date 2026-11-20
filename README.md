# 小艺聊天输入导出器（Xiaoyi Input Exporter）

用 Streamlit 做的轻量网页：批量读取公开可访问的 `https://xiaoyi.huawei.com/s/<分享ID>`，从分享页 HTML 内嵌 JSON 中提取 `content` 数组的 `query` 字段。

- 每行粘贴一个小艺分享链接；最多 20 个，自动去重。
- **单网页**：下载一个 TXT；**多个网页**：下载 ZIP，内含每个成功网页对应的一个 TXT。
- TXT 采用 UTF-8 with BOM（Windows 记事本友好）；每条用户输入一行，输入内换行和连续空白合并为空格，保留条目顺序和重复输入。
- 逐条反馈成功数量和失败原因。某个网页失败不影响其他网页。
- 只请求指定 HTTPS 域名，不跟随重定向，限制下载大小。

## 本地运行

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

浏览器打开终端给出的本地地址（通常为 http://localhost:8501）。

## 部署到 Streamlit Community Cloud

1. 新建 GitHub 仓库（例如 `xiaoyi-input-exporter`），上传此目录中的全部文件（尤其 `app.py`、`extractor.py` 和 `requirements.txt`）。
2. 登录 [Streamlit Community Cloud](https://share.streamlit.io/)，连接 GitHub。
3. 点击 **Create app**，选择仓库及 `main` 分支，主文件路径填 `app.py`，点击部署。
4. 部署成功后分享 `*.streamlit.app` 网址。

> GitHub Pages 本身无法运行 Python 服务器；需要 Streamlit Community Cloud 等 Python 托管服务。免费托管会有资源限制和休眠机制。

## 适用范围及隐私

本项目只提取分享页面内嵌 JSON 的 `query`（用户输入），**不导出小艺回答**。如果华为更改数据格式、页面需要登录，或从 Streamlit 托管服务器无法访问华为站点，提取会失败。

请只提交你有权访问和导出的分享链接。部署服务器会接收链接并向华为请求页面；代码不主动写入聊天内容、Cookie 或持久化缓存，但服务器提供商可能记录请求元数据。避免在公开渠道发布含敏感信息的分享链接。

本项目并非华为官方产品。

## 测试

```bash
python -m unittest discover -s tests -v
```
