import json
import argparse
import tempfile
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cgi

from word_to_questions_json import parse_lines, read_docx_text


ROOT = Path(__file__).resolve().parent


class PracticeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path == "/api/convert-word":
            self.convert_word()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def convert_word(self):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_json({"error": "请上传 Word .docx 文件。"}, HTTPStatus.BAD_REQUEST)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )
        file_item = form["docx"] if "docx" in form else None
        if file_item is None or not getattr(file_item, "filename", ""):
            self.send_json({"error": "没有收到 Word 文件。"}, HTTPStatus.BAD_REQUEST)
            return

        filename = Path(file_item.filename).name
        if not filename.lower().endswith(".docx"):
            self.send_json({"error": "目前只支持 .docx 文件。"}, HTTPStatus.BAD_REQUEST)
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(file_item.file.read())

        try:
            lines = read_docx_text(temp_path)
            questions = parse_lines(lines, answers={})
        except Exception as exc:
            self.send_json({"error": f"Word 解析失败：{exc}"}, HTTPStatus.BAD_REQUEST)
            return
        finally:
            temp_path.unlink(missing_ok=True)

        for index, question in enumerate(questions, start=1):
            question["uid"] = f"{filename}-{index}"

        output = {
            "filename": filename,
            "count": len(questions),
            "answerlessCount": sum(1 for item in questions if not item.get("answer")),
            "questions": questions,
        }
        self.send_json(output)

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="选择题练习本地服务器")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("localhost", args.port), PracticeHandler)
    print(f"选择题练习程序已启动：http://localhost:{args.port}/choice_practice_demo.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
