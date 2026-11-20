"""Streamlit interface for extracting user inputs from Xiaoyi share links."""
from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from extractor import ExtractionError, fetch_queries, parse_input_urls, queries_to_txt

st.set_page_config(page_title="小艺聊天输入导出", page_icon="💬", layout="centered")
st.title("💬 小艺聊天输入导出")
st.caption("提取华为小艺分享页中的用户输入（query），一条输入占 TXT 一行。")
st.info("仅处理公开可访问的小艺分享链接；分享链接及聊天内容可能包含隐私，请谨慎使用。")

links = st.text_area(
    "小艺分享链接（每行一个，最多 20 个）",
    placeholder="https://xiaoyi.huawei.com/s/xxxx\nhttps://xiaoyi.huawei.com/s/另一个分享ID",
    height=150,
)

if st.button("开始提取", type="primary", use_container_width=True):
    # Clear previous result so an invalid new submission never downloads stale content.
    st.session_state.pop("export_result", None)
    try:
        items = parse_input_urls(links)
    except ExtractionError as exc:
        st.error(str(exc))
    else:
        results = []
        progress = st.progress(0, text="正在提取…")
        for idx, (url, share_id) in enumerate(items, 1):
            try:
                queries = fetch_queries(url)
                results.append({"url": url, "share_id": share_id, "queries": queries, "error": None})
            except ExtractionError as exc:
                results.append({"url": url, "share_id": share_id, "queries": [], "error": str(exc)})
            progress.progress(idx / len(items), text=f"已处理 {idx}/{len(items)} 条链接")
        progress.empty()
        st.session_state["export_result"] = results

results = st.session_state.get("export_result")
if results:
    successes = [item for item in results if item["error"] is None]
    errors = [item for item in results if item["error"] is not None]
    st.subheader("提取结果")
    st.write(f"成功 **{len(successes)}** 个网页，失败 **{len(errors)}** 个网页，共提取 **{sum(len(x['queries']) for x in successes)}** 条输入。")
    for result in results:
        if result["error"]:
            st.error(f"{result['share_id']}：{result['error']}")
        else:
            st.success(f"{result['share_id']}：{len(result['queries'])} 条输入")

    if successes:
        if len(successes) == 1 and len(results) == 1:
            item = successes[0]
            st.download_button(
                "📄 下载 TXT",
                data=queries_to_txt(item["queries"]),
                file_name=f"xiaoyi_{item['share_id']}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        else:
            buffer = BytesIO()
            with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
                for idx, item in enumerate(successes, 1):
                    archive.writestr(
                        f"{idx:02d}_xiaoyi_{item['share_id']}.txt",
                        queries_to_txt(item["queries"]),
                    )
            st.download_button(
                "📦 下载 ZIP（每个成功网页一个 TXT）",
                data=buffer.getvalue(),
                file_name="xiaoyi_inputs.zip",
                mime="application/zip",
                use_container_width=True,
            )
        with st.expander("预览提取的输入"):
            for item in successes:
                st.markdown(f"**{item['share_id']}**")
                st.code("\n".join(item["queries"][:20]), language=None)
                if len(item["queries"]) > 20:
                    st.caption("只预览前 20 条；下载内容包含全部提取结果。")

st.caption("内容只用于本次处理，不写入服务器文件或持久化缓存；托管服务的运行日志及网络基础设施仍可能记录请求元数据。")
