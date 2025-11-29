import os
import sys
import re
from notion_client import Client

# ------------------------
# 1. 配置区域 (Configuration)
# ------------------------
# 从 GitHub Secrets 获取密钥
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 检查密钥是否存在
if not NOTION_TOKEN or not DATABASE_ID:
    print("❌ 错误：未设置 NOTION_TOKEN 或 NOTION_DATABASE_ID")
    sys.exit(1)

# 初始化 Notion 客户端
notion = Client(auth=NOTION_TOKEN)

# ------------------------
# 2. Markdown 转换工具 (Helper Functions)
# ------------------------

def richtext_to_plain(rich_text_list):
    """把 Notion 的富文本转换为 Markdown 格式的纯文本"""
    text_content = ""
    for x in rich_text_list:
        plain = x.get("plain_text", "")
        
        # 处理行内公式 (Inline Equation) -> 转换为 $E=mc^2$
        if x.get("type") == "equation":
            expr = x.get("equation", {}).get("expression", plain)
            plain = f"${expr}$" 
        # 处理链接
        elif x.get("href"):
            plain = f"[{plain}]({x.get('href')})"
        # 处理加粗、代码样式
        else:
            anns = x.get("annotations", {})
            if anns.get("code"): plain = f"`{plain}`"
            elif anns.get("bold"): plain = f"**{plain}**"
            elif anns.get("italic"): plain = f"*{plain}*"
            elif anns.get("strikethrough"): plain = f"~~{plain}~~"
            
        text_content += plain
    return text_content

def block_to_markdown(block):
    """把 Notion 的 Block 转换为 Markdown 字符串"""
    b_type = block["type"]
    content = ""
    
    # 获取该 Block 的富文本内容
    rich_text = block.get(b_type, {}).get("rich_text", [])
    text = richtext_to_plain(rich_text) if rich_text else ""

    try:
        # --- 标题 ---
        if b_type == "heading_1":
            content = f"# {text}\n\n"
        elif b_type == "heading_2":
            content = f"## {text}\n\n"
        elif b_type == "heading_3":
            content = f"### {text}\n\n"
        
        # --- 正文与列表 ---
        elif b_type == "paragraph":
            content = f"{text}\n\n"
        elif b_type == "bulleted_list_item":
            content = f"- {text}\n"
        elif b_type == "numbered_list_item":
            content = f"1. {text}\n"
        elif b_type == "to_do":
            checked = "x" if block["to_do"].get("checked") else " "
            content = f"- [{checked}] {text}\n"

        # --- 代码块 ---
        elif b_type == "code":
            lang = block["code"].get("language", "text")
            content = f"```{lang}\n{text}\n```\n\n"

        # --- 数学公式块 (独立显示) ---
        elif b_type == "equation":
            expr = block["equation"].get("expression", "")
            content = f"$$\n{expr}\n$$\n\n"

        # --- 引用与标注 ---
        elif b_type == "quote":
            content = f"> {text}\n\n"
        elif b_type == "callout":
            icon = block["callout"].get("icon", {}).get("emoji", "💡")
            content = f"> {icon} **{text}**\n\n"

        # --- 图片 ---
        elif b_type == "image":
            url = block["image"].get("file", {}).get("url") or block["image"].get("external", {}).get("url")
            content = f"![image]({url})\n\n"
        
        # --- 分割线 ---
        elif b_type == "divider":
            content = "---\n\n"

        # 递归处理子 Block (例如列表下的缩进内容)
        if block.get("has_children"):
            children = notion.blocks.children.list(block["id"]).get("results", [])
            for child in children:
                # 给子内容增加缩进 (简单处理)
                child_md = block_to_markdown(child)
                if b_type in ["bulleted_list_item", "numbered_list_item"]:
                    content += "    " + child_md
                else:
                    content += child_md
                
    except Exception as e:
        print(f"⚠️ 解析 Block 出错 ({b_type}): {e}")
        pass

    return content

# ------------------------
# 3. 主程序逻辑 (Main Logic)
# ------------------------

def sync():
    print("🔄 开始连接 Notion 数据库...")
    
    try:
        # 查询数据库
        # 这里为了保险，暂时不加 filter，把所有笔记都抓下来
        # 如果你想只抓 'Done' 的，可以在这里加 filter 参数
        response = notion.databases.query(database_id=DATABASE_ID)
        pages = response.get("results", [])
    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        print("请检查：1. Database ID 是否正确 2. 是否已将 Integration 邀请到页面 (Connect to)")
        sys.exit(1)

    print(f"🔍 成功获取 {len(pages)} 篇笔记")

    for page in pages:
        props = page["properties"]
        
        # --- A. 获取标题 (Name) ---
        # 注意：你的表格第一列名字叫 "Name"
        title_obj = props.get("Name", {}).get("title", [])
        if not title_obj:
            print("⚠️ 跳过无标题页面")
            continue
        title = title_obj[0]["plain_text"]
        
        # --- B. 获取分类 (Category) ---
        # 注意：你的分类列名字叫 "Category"
        category = "Uncategorized" # 默认分类
        cat_prop = props.get("Category", {}).get("select") or props.get("Category", {}).get("multi_select")
        
        # 兼容单选(Select)和多选(Multi-select)
        if cat_prop:
            if isinstance(cat_prop, list) and len(cat_prop) > 0:
                 category = cat_prop[0]["name"] # 如果是多选，取第一个
            elif isinstance(cat_prop, dict):
                 category = cat_prop["name"]    # 如果是单选
        
        # --- C. 清理非法字符 (Sanitize) ---
        # 防止文件名里出现 / \ : * ? " < > | 这些 Windows/Linux 不允许的字符
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        safe_category = re.sub(r'[\\/*?:"<>|]', "", category).strip()
        
        print(f"📥 正在同步: [{safe_category}] {safe_title}...")

        # --- D. 获取页面内容 (Block Children) ---
        md_content = f"# {title}\n\n"
        
        # 获取该页面下的所有 Block
        blocks = notion.blocks.children.list(page["id"]).get("results", [])
        for block in blocks:
            md_content += block_to_markdown(block)
            
        # --- E. 保存文件 ---
        # 1. 自动创建文件夹 (如果不存在)
        save_dir = safe_category
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 2. 写入 Markdown 文件
        file_path = os.path.join(save_dir, f"{safe_title}.md")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
    print("✅ 同步全部完成！")

if __name__ == "__main__":
    sync()
