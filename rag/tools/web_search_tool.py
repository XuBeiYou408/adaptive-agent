from langchain.tools import tool
from duckduckgo_search import DDGS

# ==================== 网页搜索引擎工具 ====================
@tool
def wangye_sousuo_tool(query: str) -> str:
    """
    使用搜索引擎从互联网获取最新信息。
    适用于：知识库检索不到结果、询问时效性问题、外部公共常识或最新开源技术更新。
    输入：具体的搜索引擎关键词或问题。
    输出：前 5 条搜索结果的标题、链接和摘要。
    """
    try:
        jieguo = []
        with DDGS() as ddgs:
            # 获取最相关的 5 条搜索结果
            for r in ddgs.text(query, max_results=5):
                title = r.get('title', '无标题')
                link = r.get('href', '无链接')
                body = r.get('body', '无摘要')
                jieguo.append(f"【{title}】\n链接：{link}\n内容：{body}")
        
        if not jieguo:
            return "网页搜索未召回任何结果。"
        
        return "\n\n".join(jieguo)
    except Exception as e:
        return f"网页搜索服务调用失败：{str(e)}"
