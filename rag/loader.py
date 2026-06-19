import os
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader

from config import folder_path


def load_all_documents():
    # ==================== 数据源处理，获取所有文件,并分类成pdf和md ====================
    pdf_list = []
    md_list = []
    file_count = {'pdf': 0, 'md': 0}
    print('正在扫描处理本地文件中', '.' * 80)
    for root, dis, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.pdf'):
                try:
                    a = PyMuPDFLoader(os.path.join(root, file))
                    pdf_list.extend(a.load())
                    file_count['pdf'] += 1
                except Exception as e:
                    print(f'处理文件 {file} 时出错：{e}')
            elif file.endswith('.md'):
                try:
                    b = TextLoader(os.path.join(root, file), encoding='utf-8')
                    md_list.extend(b.load())
                    file_count['md'] += 1
                except Exception as e:
                    print(f'处理文件 {file} 时出错：{e}')
    print(f'处理完成，共处理 {file_count["pdf"]} 个 PDF 文件和 {file_count["md"]} 个 Markdown 文件。')
    return pdf_list, md_list, file_count
