import urllib.request
import urllib.parse
import ssl
import html
import re
from html.parser import HTMLParser
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLineEdit, QPushButton, QLabel

try:
    import js2py
    JS_AVAILABLE = True
except ImportError:
    JS_AVAILABLE = False

class FormContext:
    def __init__(self, action, method, base_url):
        self.action = action
        self.method = method.upper() if method else 'GET'
        self.base_url = base_url
        self.inputs = []

class SLREHTMLParser(HTMLParser):
    """The core SLRE HTML parsing engine."""
    def __init__(self, container_layout, base_url, load_url_callback, link_click_callback, script_collector, is_dark_mode):
        super().__init__()
        self.layout = container_layout
        self.base_url = base_url
        self.load_url_callback = load_url_callback
        self.link_click_callback = link_click_callback
        self.script_collector = script_collector
        self.is_dark_mode = is_dark_mode

        self.current_text = ""
        self.in_script = False
        self.in_style = False
        self.is_bold = False
        self.is_italic = False
        self.current_href = None
        self.current_form = None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        attr_dict = dict(attrs)

        if t == 'script':
            self.flush_text()
            self.in_script = True
            return
        if t in {'style', 'head', 'meta', 'link'}:
            self.flush_text()
            self.in_style = True
            return

        if self.in_script or self.in_style:
            return

        if t == 'form':
            self.flush_text()
            action = attr_dict.get('action', '')
            method = attr_dict.get('method', 'GET')
            self.current_form = FormContext(action, method, self.base_url)

        elif t == 'input':
            self.flush_text()
            input_type = attr_dict.get('type', 'text').lower()
            name = attr_dict.get('name', '')
            value = attr_dict.get('value', '')

            if input_type in {'text', 'search', 'email', 'password'}:
                line_edit = QLineEdit()
                line_edit.setPlaceholderText(attr_dict.get('placeholder', ''))
                line_edit.setText(value)
                self.layout.addWidget(line_edit)

                if self.current_form and name:
                    self.current_form.inputs.append((name, line_edit))

            elif input_type in {'submit', 'button'}:
                btn_text = attr_dict.get('value', 'Submit')
                btn = QPushButton(btn_text)
                self.layout.addWidget(btn)

                if self.current_form:
                    form_ref = self.current_form
                    def make_submit_handler(f):
                        def handle_submit():
                            params = []
                            for name, line_edit in f.inputs:
                                val = line_edit.text()
                                params.append(f"{urllib.parse.quote(name)}={urllib.parse.quote(val)}")
                            query_str = "&".join(params)

                            action_url = f.action
                            if not action_url:
                                target_url = f.base_url
                            elif action_url.startswith('http'):
                                target_url = action_url
                            elif action_url.startswith('/'):
                                parsed_base = urllib.parse.urlparse(f.base_url)
                                target_url = f"{parsed_base.scheme}://{parsed_base.netloc}{action_url}"
                            else:
                                base = f.base_url.rsplit('/', 1)[0]
                                target_url = f"{base}/{action_url}"

                            if f.method == 'GET':
                                separator = '&' if '?' in target_url else '?'
                                final_url = f"{target_url}{separator}{query_str}" if query_str else target_url
                                self.load_url_callback(final_url)
                            else:
                                data = query_str.encode('utf-8')
                                self.load_url_callback(target_url, data=data, method='POST')
                        return handle_submit

                    btn.clicked.connect(make_submit_handler(form_ref))

        elif t == 'img':
            self.flush_text()
            src = attr_dict.get('src', '')
            if src:
                if not src.startswith('http'):
                    parsed_base = urllib.parse.urlparse(self.base_url)
                    if src.startswith('/'):
                        src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
                    else:
                        base = self.base_url.rsplit('/', 1)[0]
                        src = f"{base}/{src}"

                try:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    img_req = urllib.request.Request(src, headers={'User-Agent': 'SLRE-Engine/1.0'})
                    with urllib.request.urlopen(img_req, context=ssl_context, timeout=5) as img_resp:
                        img_data = img_resp.read()

                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    if not pixmap.isNull():
                        img_label = QLabel()
                        if pixmap.width() > 700:
                            pixmap = pixmap.scaledToWidth(700, Qt.TransformationMode.SmoothTransformation)
                        img_label.setPixmap(pixmap)
                        self.layout.addWidget(img_label)
                except Exception:
                    pass

        elif t in {'b', 'strong'}:
            self.flush_text()
            self.is_bold = True
        elif t in {'i', 'em'}:
            self.flush_text()
            self.is_italic = True
        elif t == 'a':
            self.flush_text()
            self.current_href = attr_dict.get('href', '#')
        elif t in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.flush_text()
            self.is_bold = True
        elif t in {'br', 'tr', 'p', 'div', 'li'}:
            self.flush_text()
            if t == 'br':
                self.layout.addWidget(QLabel("<br>"))
        elif t in {'td', 'th'}:
            self.current_text += "   "
        elif t == 'hr':
            self.flush_text()
            hr_color = "#555555" if self.is_dark_mode else "#cccccc"
            self.layout.addWidget(QLabel(f"<hr style='border: none; border-top: 1px solid {hr_color}; margin: 4px 0;'>"))

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == 'script':
            self.in_script = False
            return
        if t in {'style', 'head', 'meta', 'link'}:
            self.in_style = False
            return

        if self.in_script or self.in_style:
            return

        if t in {'b', 'strong'}:
            self.flush_text()
            self.is_bold = False
        elif t in {'i', 'em'}:
            self.flush_text()
            self.is_italic = False
        elif t == 'a':
            self.flush_text()
            self.current_href = None
        elif t in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.flush_text()
            self.is_bold = False
        elif t == 'form':
            self.current_form = None
        elif t in {'tr', 'p', 'div', 'li', 'td', 'th'}:
            self.flush_text()

    def handle_data(self, data):
        if self.in_script:
            self.script_collector.append(data)
            return
        if self.in_style:
            return
        self.current_text += data

    def flush_text(self):
        text = self.current_text.strip()
        if text:
            escaped = html.escape(text)
            if self.is_bold:
                escaped = f"<b>{escaped}</b>"
            if self.is_italic:
                escaped = f"<i>{escaped}</i>"
            if self.current_href:
                target = self.current_href
                if not target.startswith('http') and not target.startswith('about:') and not target.startswith('slre://'):
                    parsed_base = urllib.parse.urlparse(self.base_url)
                    if target.startswith('/'):
                        target = f"{parsed_base.scheme}://{parsed_base.netloc}{target}"
                    else:
                        base = self.base_url.rsplit('/', 1)[0]
                        target = f"{base}/{target}"
                link_color = "#58a6ff" if self.is_dark_mode else "#0066cc"
                escaped = f"<a href='{target}' style='color: {link_color}; text-decoration: underline;'>{escaped}</a>"

            label = QLabel(escaped)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
            label.setOpenExternalLinks(False)

            def handle_link_click(url_str):
                if url_str:
                    self.link_click_callback(url_str)
            label.linkActivated.connect(handle_link_click)

            text_color = "#ffffff" if self.is_dark_mode else "#222222"
            label.setStyleSheet(f"color: {text_color}; font-family: Arial, sans-serif; font-size: 13px; line-height: 1.3;")
            self.layout.addWidget(label)

        self.current_text = ""
