import base64
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

APP_DIR = Path(__file__).resolve().parent
LIB_DIR = APP_DIR / "lib"
if LIB_DIR.is_dir():
    sys.path.insert(0, str(LIB_DIR))

import pypdfium2 as pdfium


STATIC_DIR = APP_DIR / "static"
INDEX_FILE = APP_DIR / "templates" / "index.html"
ALLOWED_FORMATS = {"png", "jpg", "jpeg", "webp"}
MAX_JSON_BYTES = 300 * 1024 * 1024


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def parse_page_range(text, page_count):
    """Parse a page range such as '1-3,5' into a zero-based sorted index list."""
    if not text or not str(text).strip():
        return list(range(page_count))

    raw = str(text).strip()
    if not re.fullmatch(r"[0-9,\-\s]+", raw):
        raise ValueError("页码范围只能包含数字、逗号、连字符和空格")

    selected = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start_text = start_text.strip()
            end_text = end_text.strip()
            if not start_text or not end_text:
                raise ValueError("页码范围格式不正确")
            start = int(start_text)
            end = int(end_text)
            if start > end:
                start, end = end, start
            if start < 1 or end > page_count:
                raise ValueError(f"页码范围超出文档范围 1-{page_count}")
            selected.update(range(start - 1, end))
        else:
            page = int(part)
            if page < 1 or page > page_count:
                raise ValueError(f"页码超出文档范围 1-{page_count}")
            selected.add(page - 1)

    if not selected:
        raise ValueError("没有选择任何页码")
    return sorted(selected)


def render_pdf(pdf_bytes, output_dir, image_format, dpi, page_range, prefix):
    output_dir = Path(output_dir).expanduser()
    if not output_dir.is_absolute():
        raise ValueError("输出目录必须是绝对路径")
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        page_count = len(pdf)
        if page_count == 0:
            raise ValueError("PDF 文档没有可转换的页面")

        indexes = parse_page_range(page_range, page_count)
        fmt = image_format.lower()
        if fmt == "jpg":
            fmt = "jpeg"
        scale = max(0.1, dpi / 72.0)
        prefix = prefix.strip() or "page"
        prefix = re.sub(r"[\\/:*?\"<>|]", "_", prefix)

        results = []
        for number in indexes:
            page = pdf[number]
            try:
                bitmap = page.render(scale=scale)
                image = bitmap.to_pil()
                filename = f"{prefix}_page_{number + 1:03d}.{fmt}"
                destination = output_dir / filename
                if fmt in ("jpg", "jpeg"):
                    image = image.convert("RGB")
                image.save(destination, quality=92 if fmt in ("jpg", "jpeg", "webp") else None)
                results.append({"page": number + 1, "path": str(destination), "name": filename})
            finally:
                page.close()
        return results
    finally:
        pdf.close()


def choose_folder():
    """Open a native folder picker and return the selected path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    try:
        selected = filedialog.askdirectory(title="选择图片保存目录", mustexist=True)
        return selected or ""
    finally:
        root.destroy()


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "PDFToImages/1.0"

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self.serve_file(INDEX_FILE, "text/html; charset=utf-8")
        if path.startswith("/static/"):
            relative = path[len("/static/"):]
            file_path = (STATIC_DIR / relative).resolve()
            if not str(file_path).startswith(str(STATIC_DIR.resolve())):
                self.send_error(403)
                return
            content_types = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".svg": "image/svg+xml",
            }
            return self.serve_file(file_path, content_types.get(file_path.suffix, "application/octet-stream"))
        self.send_error(404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/choose-folder":
            return self.choose_folder_endpoint()
        if path != "/api/convert":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("请求内容为空")
            if length > MAX_JSON_BYTES:
                raise ValueError("PDF 文件过大，请选择较小的文件")

            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            pdf_base64 = payload.get("pdf")
            if not pdf_base64:
                raise ValueError("未接收到 PDF 文件")

            pdf_bytes = base64.b64decode(pdf_base64)
            image_format = str(payload.get("format", "png")).lower()
            if image_format not in ALLOWED_FORMATS:
                raise ValueError("不支持的图片格式")

            try:
                dpi = int(payload.get("dpi", 150))
            except (TypeError, ValueError):
                raise ValueError("DPI 必须是数字")
            if dpi < 36 or dpi > 600:
                raise ValueError("DPI 应在 36 到 600 之间")

            output_dir = str(payload.get("outputDir", "")).strip()
            if not output_dir:
                raise ValueError("请填写输出目录")
            page_range = str(payload.get("pageRange", "")).strip()
            prefix = str(payload.get("prefix", "page"))

            results = render_pdf(
                pdf_bytes=pdf_bytes,
                output_dir=output_dir,
                image_format=image_format,
                dpi=dpi,
                page_range=page_range,
                prefix=prefix,
            )
            send_json(self, 200, {"ok": True, "files": results, "count": len(results)})
        except (ValueError, json.JSONDecodeError, base64.binascii.Error) as exc:
            send_json(self, 400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            send_json(self, 500, {"ok": False, "error": f"转换失败：{exc}"})

    def choose_folder_endpoint(self):
        try:
            selected = choose_folder()
            if not selected:
                send_json(self, 200, {"ok": False, "path": "", "error": "未选择文件夹"})
                return
            send_json(self, 200, {"ok": True, "path": selected})
        except Exception as exc:
            send_json(self, 500, {"ok": False, "error": f"无法打开文件夹选择窗口：{exc}"})

    def serve_file(self, file_path, content_type):
        if not file_path.exists():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        sys.stdout.write("[%s] %s\n" % (self.log_date_time_string(), format % args))


def main():
    host = "127.0.0.1"
    port = 8765
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    server = ThreadingHTTPServer((host, port), RequestHandler)
    print(f"PDF 转图片服务已启动：http://{host}:{port}")
    print("按 Ctrl+C 停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

#辛凯