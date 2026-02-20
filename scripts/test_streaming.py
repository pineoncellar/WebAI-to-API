import json
import httpx
import sys

def test_streaming():
    url = "http://localhost:6969/v1/chat/completions"
    
    # 修改这里的 API Key，如果你的 config.conf 中设置自了 api_key
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 1145141919810889464" 
    }

    payload = {
        "model": "gemini-3.0-flash",
        "messages": [
            {"role": "user", "content": "帮我写一段python代码，实现从一段文本中找到特定词语位置的功能"}
        ],
        "stream": True
    }

    print(f"正在向 {url} 发送流式请求...")
    
    try:
        with httpx.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                # 尝试读取错误信息
                try:
                    error_detail = response.read().decode()
                    print(f"错误详情: {error_detail}")
                except:
                    pass
                return

            print("收到响应，开始流式输出：\n" + "-"*20)
            
            full_content = ""
            for line in response.iter_lines():
                if not line.strip():
                    continue
                
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        print("\n" + "-"*20 + "\n传输完成 [DONE]")
                        break
                    
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        
                        # 处理思考过程 (Reasoning Content)
                        reasoning = delta.get("reasoning_content")
                        if reasoning:
                            print(f"【THOUGHT: {reasoning}】", end="", flush=True)
                        
                        # 处理文本内容
                        content = delta.get("content")
                        if content:
                            full_content += content
                            print(f"[{content}]", end="", flush=True)
                            
                    except json.JSONDecodeError:
                        print(f"\n解析 JSON 失败: {data_str}")

    except httpx.ConnectError:
        print("错误: 无法连接到服务器。请确保 WebAI-to-API 服务器已在 localhost:6969 运行。")
    except Exception as e:
        print(f"\n发生错误: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_streaming()
