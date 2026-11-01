import sys
import urllib.request
import urllib.parse
import ssl
import html
import re
import platform
import webbrowser
import os
from html.parser import HTMLParser

try:
    import psutil
except ImportError:
    psutil = None

try:
    import js2py
    JS_AVAILABLE = True
except Exception:
    JS_AVAILABLE = False

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QLabel, QMessageBox
)

ACTIVE_WINDOWS = []

def get_memory_usage():
    """Fetches live memory usage of the running application instance."""
    try:
        if psutil:
            process = psutil.Process(os.getpid())
            mem_bytes = process.memory_info().rss
            return f"{mem_bytes / (1024 * 1024):.2f} MB"
        else:
            import resource
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            mem_bytes = rusage.ru_maxrss if sys.platform == 'darwin' else rusage.ru_maxrss * 1024
            return f"{mem_bytes / (1024 * 1024):.2f} MB"
    except Exception:
        return "N/A"

class FormContext:
    def __init__(self, action, method, base_url):
        self.action = action
        self.method = method.upper() if method else 'GET'
        self.base_url = base_url
        self.inputs = []

class SLREHTMLParser(HTMLParser):
    """The core SLRE HTML parsing and rendering engine."""
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

class SLREWindow(QMainWindow):
    """Single-window SLRE browser shell with native macOS menu bar and Dark Mode support."""
    def __init__(self, initial_url="about:blank", is_dark_mode=False):
        super().__init__()
        self.is_dark_mode = is_dark_mode
        self.setWindowTitle("SLRE - Blank")
        self.resize(850, 650)

        self.history = []
        self.history_index = -1

        self.init_menu_bar()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)

        self.back_btn = QPushButton("←")
        self.back_btn.setFixedWidth(35)
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self.go_back)

        self.fwd_btn = QPushButton("→")
        self.fwd_btn.setFixedWidth(35)
        self.fwd_btn.setEnabled(False)
        self.fwd_btn.clicked.connect(self.go_forward)

        self.reload_btn = QPushButton("⟳")
        self.reload_btn.setFixedWidth(35)
        self.reload_btn.clicked.connect(self.reload_page)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search DuckDuckGo Lite...")
        self.url_bar.returnPressed.connect(self.load_entered_url)

        self.go_btn = QPushButton("Go")
        self.go_btn.setFixedWidth(45)
        self.go_btn.clicked.connect(self.load_entered_url)

        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.fwd_btn)
        nav_layout.addWidget(self.reload_btn)
        nav_layout.addWidget(self.url_bar)
        nav_layout.addWidget(self.go_btn)

        main_layout.addLayout(nav_layout)

        self.scroll_content = QWidget()
        self.document_layout = QVBoxLayout()
        self.document_layout.setContentsMargins(4, 4, 4, 4)
        self.document_layout.setSpacing(4)
        self.document_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_content.setLayout(self.document_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)

        main_layout.addWidget(self.scroll_area)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.apply_theme()
        self.load_url(initial_url)

    def toggle_appearance(self):
        """Toggles between Light Mode and Dark Mode dynamically."""
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        self.reload_page()

    def apply_theme(self):
        """Applies stylesheet rules depending on current Dark/Light mode state."""
        if self.is_dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e1e; color: #ffffff; }
                QLineEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #444444; padding: 4px; border-radius: 3px; font-family: Arial; font-size: 13px; }
                QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #444444; padding: 4px 10px; border-radius: 3px; font-family: Arial; font-size: 13px; }
                QPushButton:hover { background-color: #3d3d3d; }
                QScrollArea { background-color: #1e1e1e; border: none; }
            """)
        else:
            self.setStyleSheet("")

    def init_menu_bar(self):
        """Creates the native macOS menu bar (File, Edit, View, Appearance, Window, Help)."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")
        new_win_action = file_menu.addAction("New Window")
        new_win_action.setShortcut("Ctrl+N")
        new_win_action.triggered.connect(lambda: self.open_new_window("about:blank"))

        close_action = file_menu.addAction("Close Window")
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self.close)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Cut").triggered.connect(lambda: QApplication.focusWidget().cut() if hasattr(QApplication.focusWidget(), 'cut') else None)
        edit_menu.addAction("Copy").triggered.connect(lambda: QApplication.focusWidget().copy() if hasattr(QApplication.focusWidget(), 'copy') else None)
        edit_menu.addAction("Paste").triggered.connect(lambda: QApplication.focusWidget().paste() if hasattr(QApplication.focusWidget(), 'paste') else None)

        # View Menu
        view_menu = menubar.addMenu("&View")
        reload_action = view_menu.addAction("Reload")
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self.reload_page)

        home_action = view_menu.addAction("SLRE Home")
        home_action.triggered.connect(lambda: self.load_url("slre://home"))

        # Appearance Menu
        appearance_menu = menubar.addMenu("&Appearance")
        toggle_theme_action = appearance_menu.addAction("Toggle Dark / Light Mode")
        toggle_theme_action.setShortcut("Ctrl+D")
        toggle_theme_action.triggered.connect(self.toggle_appearance)

        # Window Menu
        window_menu = menubar.addMenu("&Window")
        window_menu.addAction("Minimize").triggered.connect(self.showMinimized)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        about_action = help_menu.addAction("About SLRE")
        about_action.triggered.connect(lambda: self.load_url("slre://about"))

    def open_new_window(self, url="about:blank"):
        new_win = SLREWindow(initial_url=url, is_dark_mode=self.is_dark_mode)
        ACTIVE_WINDOWS.append(new_win)
        new_win.show()

    def clear_document(self):
        while self.document_layout.count():
            item = self.document_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def load_slre_home_page(self):
        """Loads the ASCII logo and SLRE Browser 1.0 splash screen."""
        self.clear_document()
        self.setWindowTitle("SLRE - Home")

        title_color = "#58a6ff" if self.is_dark_mode else "#1a73e8"
        title = QLabel(f"<h1 style='color: {title_color}; margin-bottom: 0px;'>SLRE Browser 1.0</h1>")
        self.document_layout.addWidget(title)

        hr_color = "#555555" if self.is_dark_mode else "#cccccc"
        hr = QLabel(f"<hr style='border: none; border-top: 1px solid {hr_color};'>")
        self.document_layout.addWidget(hr)

        art_color = "#e0e0e0" if self.is_dark_mode else "#333333"
        ascii_art = QLabel(
            f"<pre style='font-family: Courier New; color: {art_color}; margin: 0;'>"
            "  ####    #     #####   ##### \n"
            " #        #     #    #  #     \n"
            "  ###     #     #####   ##### \n"
            "     #    #     #   #   #     \n"
            "  ####    ##### #    #  ##### "
            "</pre>"
        )
        self.document_layout.addWidget(ascii_art)

        status_color = "#79c0ff" if self.is_dark_mode else "#0d6efd"
        status_text = "Status: Welcome to SLRE Browser 1.0! Type a URL or search DuckDuckGo Lite above."
        status = QLabel(f"<b style='color: {status_color};'>{status_text}</b>")
        self.document_layout.addWidget(status)

        self.push_history("slre://home")

    def load_about_page(self):
        """Loads the slre://about system details page."""
        self.clear_document()
        self.setWindowTitle("SLRE - About")

        title_color = "#58a6ff" if self.is_dark_mode else "#1a73e8"
        title = QLabel(f"<h1 style='color: {title_color}; margin-bottom: 0px;'>SLRE Engine 1.0</h1>")
        self.document_layout.addWidget(title)

        sub_color = "#aaaaaa" if self.is_dark_mode else "#555555"
        sub = QLabel(f"<b>Simple Lightweight Rendering Engine</b>")
        sub.setStyleSheet(f"color: {sub_color}; font-family: Arial; font-size: 14px;")
        self.document_layout.addWidget(sub)

        hr_color = "#555555" if self.is_dark_mode else "#cccccc"
        hr = QLabel(f"<hr style='border: none; border-top: 1px solid {hr_color};'>")
        self.document_layout.addWidget(hr)

        text_color = "#ffffff" if self.is_dark_mode else "#222222"
        info_text = (
            f"<b>Made with &lt;3 by DanDevProjects (dannyl0v3sl1nux)</b><br>"
            f"This is an open source project!<br>"
            f"One of my AI VS Code experiments, generated By Flash-Lite High!<br><br>"
            f"<b>Engine Specs:</b> SLRE Engine 1.0 Built with Python and Qt<br>"
            f"<b>System Platform:</b> {platform.platform()}<br>"
            f"<b>Python Version:</b> {platform.python_version()}<br>"
            f"<b>Live App Memory Usage:</b> {get_memory_usage()}<br>"
        )
        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color: {text_color}; font-family: Arial; font-size: 13px; line-height: 1.5;")
        self.document_layout.addWidget(info_lbl)

        support_btn = QPushButton("Support me at github.com/DanDevProjects")
        support_btn.clicked.connect(lambda: webbrowser.open("https://github.com/DanDevProjects"))
        self.document_layout.addWidget(support_btn)

        self.push_history("slre://about")

    def push_history(self, url):
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append(url)
        self.history_index = len(self.history) - 1
        self.update_nav_buttons()

    def update_nav_buttons(self):
        self.back_btn.setEnabled(self.history_index > 0)
        self.fwd_btn.setEnabled(self.history_index < len(self.history) - 1)

    def load_entered_url(self):
        url = self.url_bar.text().strip()
        if not url:
            return

        if url.lower() == "slre://about":
            self.load_url("slre://about")
            return

        if url.lower() == "slre://home":
            self.load_url("slre://home")
            return

        if url.lower() in {"about:blank", "nothing"}:
            self.load_url("about:blank")
            return

        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("slre://"):
            if "." in url and " " not in url:
                url = "https://" + url
            else:
                search_query = url
                ddg_url = "https://lite.duckduckgo.com/lite/"
                post_data = urllib.parse.urlencode({'q': search_query}).encode('utf-8')
                self.load_url(ddg_url, data=post_data, method='POST')
                return

        self.load_url(url)

    def handle_link_click(self, url_str):
        if "github.com/DanDevProjects" in url_str:
            webbrowser.open("https://github.com/DanDevProjects")
            return
        if url_str.lower() == "slre://about":
            self.load_url("slre://about")
            return
        if url_str.lower() == "slre://home":
            self.load_url("slre://home")
            return

        reply = QMessageBox.question(
            self, "Open Link in New Window",
            f"Do you want to open this link in a new window?\n\n{url_str}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.open_new_window(url=url_str)
        else:
            self.load_url(url_str)

    def load_url(self, url, data=None, method='GET'):
        if url.lower() in {"about:blank", "nothing"}:
            self.url_bar.setText("")
            self.setWindowTitle("SLRE - Blank")
            self.clear_document()
            self.push_history("about:blank")
            return

        if url.lower() == "slre://about":
            self.url_bar.setText("slre://about")
            self.load_about_page()
            return

        if url.lower() == "slre://home":
            self.url_bar.setText("slre://home")
            self.load_slre_home_page()
            return

        self.url_bar.setText(url)
        self.setWindowTitle(f"SLRE - {url}")

        try:
            self.clear_document()

            loading_color = "#aaaaaa" if self.is_dark_mode else "#666666"
            loading_lbl = QLabel(f"<i>Loading {url}...</i>")
            loading_lbl.setStyleSheet(f"color: {loading_color};")
            self.document_layout.addWidget(loading_lbl)

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                url,
                data=data,
                headers={'User-Agent': 'SLRE-Engine/1.0'}
            )
            if method == 'POST':
                req.method = 'POST'

            with urllib.request.urlopen(req, context=ssl_context, timeout=8) as response:
                content_type = response.headers.get('Content-Type', '')

                if 'image/' in content_type:
                    img_data = response.read()
                    self.clear_document()

                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    if not pixmap.isNull():
                        img_label = QLabel()
                        if pixmap.width() > 750:
                            pixmap = pixmap.scaledToWidth(750, Qt.TransformationMode.SmoothTransformation)
                        img_label.setPixmap(pixmap)
                        self.document_layout.addWidget(img_label)
                    self.push_history(url)
                    return

                html_content = response.read().decode('utf-8', errors='ignore')

            self.clear_document()

            script_collector = []
            parser = SLREHTMLParser(
                self.document_layout, url,
                self.load_url, self.handle_link_click, script_collector, self.is_dark_mode
            )
            parser.feed(html_content)
            parser.flush_text()

            if JS_AVAILABLE and script_collector:
                try:
                    js_code = "\n".join(script_collector)
                    js2py.eval_js(js_code)
                except Exception:
                    pass

            self.push_history(url)

        except Exception as e:
            self.clear_document()
            err_color = "#f85149" if self.is_dark_mode else "#d9534f"
            text_color = "#ffffff" if self.is_dark_mode else "#222222"
            err_lbl = QLabel(f"<b style='color: {err_color};'>Failed to load URL: {url}</b><br><br><span style='color: {text_color};'>Error Details: {str(e)}</span>")
            self.document_layout.addWidget(err_lbl)

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            url = self.history[self.history_index]
            self.url_bar.setText(url if url != "about:blank" else "")
            self.load_url(url)

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            url = self.history[self.history_index]
            self.load_url(url)

    def reload_page(self):
        current_url = self.history[self.history_index]
        if current_url:
            self.load_url(current_url)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = SLREWindow(initial_url="about:blank")
    ACTIVE_WINDOWS.append(main_window)
    main_window.show()
    sys.exit(app.exec())
