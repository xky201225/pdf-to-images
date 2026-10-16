# PDF 转图片

一个本地网页工具：选择 PDF 文件，设置输出目录和图片格式，按页将 PDF 转换为 PNG、JPG 或 WebP 图片。项目已内置 `pypdfium2` 运行库，通常无需联网安装依赖。

## 使用步骤

1. 双击 `run.bat`，脚本会自动启动服务。
2. 浏览器打开 `http://127.0.0.1:8765`。
3. 选择 PDF 文件，填写要保存图片的目录（例如 `C:\Users\你的用户名\Desktop\图片`）。
4. 设置格式、DPI 和页码范围，点击“开始转换”。

如果浏览器没有自动打开，请手动访问 `http://127.0.0.1:8765`。

## 手动运行

```powershell
python app.py
```

如果内置运行库缺失，请先执行 `python -m pip install -r requirements.txt`。

停止服务：双击 `stop.bat`；如果是在命令行窗口运行，也可以按 `Ctrl+C`。
