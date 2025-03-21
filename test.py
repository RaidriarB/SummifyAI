import re

def split_text_into_chunks(text, chunk_size):
    # 统一的正则表达式：
    # .+? —— 非贪婪匹配任意字符
    # (?:\s*[，。！？；：,.!?;:]+\s*|\s+|$)
    #    —— 匹配以下三种情况之一：
    #         1. 可选空白 + 至少一个标点符号 + 可选空白
    #         2. 一个或多个空白符（不含标点）
    #         3. 文本结尾
    pattern = re.compile(r'.+?(?:\s*[，。！？；：,.!?;:]+\s*|\s+|$)')
    
    # 利用正则表达式提取各个分段
    sentences = [s for s in pattern.findall(text) if s.strip()]
    
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        #print("[" + sentence + "]")
        candidate = (current_chunk  + sentence) if current_chunk else sentence
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# 示例1：含有标点且标点前后带有空白
text1 = "这是一段测试文本 ， 包含多种标点符号 ！ 它将被正确分割 。 确保不切断句子 。这是一段测试文本，包含多种标点符号！它将被正确分割。确保不切断句子。"
print("示例1：")
for chunk in split_text_into_chunks(text1, 20):
    print(chunk)

print("\n示例2：")
# 示例2：没有标点，仅由空白符分隔
text2 = "这是一段测试文本 包含多种标点符号 它将被正确分割 确保不切断句子 这是一段测试文本，包含多种标点符号！它将被正确分割。确保不切断句子。"
for chunk in split_text_into_chunks(text2, 20):
    print(chunk)
