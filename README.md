# SummifyAI

你是否为长达几十分钟甚至一两小时的长视频网课感到头疼？这些视频整体信息密度不高，但偶尔却包含关键知识点，让人不知如何是好。

SummifyAI 能将音频或视频快速转写为文字，并通过自定义 prompt 进行总结精炼、笔记整理、摘要生成等一系列操作，大幅提升你的学习与工作效率。
- 支持多种音频和视频格式输入
- 使用 Buzz 进行本地的高质量语音转写，无需付费
- 调用 AI 智能添加标点和修正文本，大幅提高准确性（可选用超便宜的deepseek！）
- 可自定义prompt，进行生成文本摘要和关键信息提取等一系列操作
- 分步骤处理，可灵活选择执行的功能

<img src="./imgs/index.png" style="zoom:50%;" />

![](./imgs/usage.png)



## 1 安装说明

### 1.0 环境要求

- Python 3.9 或更高版本
- FFmpeg
- Buzz
- 目前只在MacOS中测试过
### 1.1 依赖安装

1. **FFmpeg 安装**
   - 官方网站：[https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
   - macOS安装方法（使用 Homebrew）：
     ```bash
     brew install ffmpeg
     ```

2. **Buzz工具安装，并使命令行能调用**
   - 官方网站：[https://github.com/chidiwilliams/buzz](https://github.com/chidiwilliams/buzz)
   - 下载应用后，需要下载所需模型。本项目中使用whisper-large-v3-turbo模型
   - 将buzz的可执行文件所在文件夹，添加到环境变量中。
    - MacOS中，可执行文件一般位于`/Applications/Buzz.app/Contents/MacOS/Buzz`
    - 因此，把这一行加到zshrc或bashrc中：`export PATH="/Applications/Buzz.app/Contents/MacOS:$PATH"`

3. **Python 依赖安装**

```bash
cd SummifyAI
pip install -r requirements.txt
```
### 1.2 配置
- 在config.py中，配置apikey，并指定使用的模型。
- prompts文件夹中，可编写多个txt文件，作为自定义的prompt，工具会分别处理。

## 2 使用方法

```bash
python main.py <input_file> [选项]
```

- `input_file`：输入的音频或视频文件路径（必需）
- `--steps`：指定要执行的步骤（默认：'1234'）
  - 1：音频预处理
  - 2：语音转写
  - 3：AI 加标点和修正
  - 4：AI 总结
- `--output-dir`：输出目录（默认：'output'）

**使用示例**

1. 执行所有步骤：
```bash
python main.py video.mp4
```

2. 只执行音频预处理和语音转写：
```bash
python main.py audio.mp3 --steps 12
```

3. 指定输出目录：
```bash
python main.py video.mp4 --output-dir my_output
```

## 其他

欢迎提需求！

buzz-whisper-large-v3-turbo 转写速度：MacbookPro M4 8线程，25min -> 205秒转写完成

调用deepseek api处理速度：慢的时候要一两分钟
