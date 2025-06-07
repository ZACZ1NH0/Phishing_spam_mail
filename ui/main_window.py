from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTextEdit, QLineEdit, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QSplitter, QFrame, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor
from services.email_service import EmailService
from services.classification_service import ClassificationService
from utils.config import APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT
import email
import os

class EmailLoaderThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, email_service):
        super().__init__()
        self.email_service = email_service

    def run(self):
        try:
            emails = self.email_service.get_emails()
            self.finished.emit(emails)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, email_service, classification_service):
        super().__init__()
        self.email_service = email_service
        self.classification_service = classification_service
        self.init_ui()

    def init_ui(self):
        """Khởi tạo giao diện chính"""
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Nút đăng xuất
        logout_button = QPushButton("Đăng xuất")
        logout_button.clicked.connect(self.logout)
        self.menuBar().setCornerWidget(logout_button, Qt.TopRightCorner)
        
        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout chính
        layout = QVBoxLayout(central_widget)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Tạo các tab
        self.create_analyzer_tab()
        self.create_inbox_tab()
        self.create_compose_tab()
        
        # Tự động chuyển đến tab hộp thư đến
        self.tab_widget.setCurrentIndex(1)
        
        # Tự động tải email sau 500ms
        QTimer.singleShot(500, self.refresh_inbox)

    def create_analyzer_tab(self):
        """Tạo tab phân tích email"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Nút mở file .eml
        open_eml_button = QPushButton("Mở file .eml")
        open_eml_button.clicked.connect(self.open_eml_file)
        layout.addWidget(open_eml_button)
        
        # Ô nhập email (chỉ hiển thị nội dung, không cho nhập tay)
        self.email_input = QTextEdit()
        self.email_input.setPlaceholderText("Chỉ hỗ trợ phân tích file .eml. Vui lòng chọn hoặc kéo thả file .eml vào đây...")
        self.email_input.setReadOnly(True)
        self.email_input.setAcceptDrops(True)
        self.email_input.installEventFilter(self)
        layout.addWidget(self.email_input)
        
        # Nút phân tích
        analyze_button = QPushButton("Phân tích")
        analyze_button.clicked.connect(self.analyze_eml_file)
        layout.addWidget(analyze_button)
        
        # Kết quả phân tích
        self.result_label = QLabel()
        layout.addWidget(self.result_label)
        
        self.tab_widget.addTab(tab, "Phân tích")
        self.current_eml_path = None

    def create_inbox_tab(self):
        """Tạo tab hộp thư đến"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Thanh tìm kiếm
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm email...")
        self.search_input.textChanged.connect(self.filter_emails)
        search_layout.addWidget(self.search_input)
        
        # Nút làm mới
        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self.refresh_inbox)
        search_layout.addWidget(refresh_button)
        
        # Nút phân loại
        classify_button = QPushButton("Phân loại")
        classify_button.clicked.connect(self.classify_selected_email)
        search_layout.addWidget(classify_button)
        
        layout.addLayout(search_layout)
        
        # Splitter cho danh sách email và nội dung
        splitter = QSplitter(Qt.Horizontal)
        
        # Danh sách email
        self.email_list = QListWidget()
        self.email_list.currentItemChanged.connect(self.show_email)
        splitter.addWidget(self.email_list)
        
        # Nội dung email
        email_content = QWidget()
        email_layout = QVBoxLayout(email_content)
        
        # Thông tin email
        self.email_info = QLabel()
        email_layout.addWidget(self.email_info)
        
        # Nội dung
        self.email_body = QTextEdit()
        self.email_body.setReadOnly(True)
        email_layout.addWidget(self.email_body)
        
        splitter.addWidget(email_content)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        
        self.loading_label = QLabel("")
        layout.addWidget(self.loading_label)
        
        self.tab_widget.addTab(tab, "Hộp thư đến")

    def create_compose_tab(self):
        """Tạo tab soạn thảo email"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Người nhận
        to_layout = QHBoxLayout()
        to_label = QLabel("Đến:")
        self.to_input = QLineEdit()
        to_layout.addWidget(to_label)
        to_layout.addWidget(self.to_input)
        layout.addLayout(to_layout)
        
        # Tiêu đề
        subject_layout = QHBoxLayout()
        subject_label = QLabel("Tiêu đề:")
        self.subject_input = QLineEdit()
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.subject_input)
        layout.addLayout(subject_layout)
        
        # Nội dung
        self.compose_body = QTextEdit()
        layout.addWidget(self.compose_body)
        
        # Nút gửi
        send_button = QPushButton("Gửi")
        send_button.clicked.connect(self.send_email)
        layout.addWidget(send_button)
        
        self.tab_widget.addTab(tab, "Soạn thảo")

    def analyze_eml_file(self):
        if not self.current_eml_path or not os.path.isfile(self.current_eml_path):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn hoặc kéo thả file .eml trước khi phân tích!")
            return
        try:
            import requests
            with open(self.current_eml_path, 'rb') as f:
                files = {'file': (os.path.basename(self.current_eml_path), f, 'application/octet-stream')}
                response = requests.post('http://localhost:5000/predict', files=files)
            if response.status_code == 200:
                result = response.json()
                label = result.get('prediction', '')
                if label == 'phishing':
                    self.result_label.setText("⚠️ Email lừa đảo!")
                    self.result_label.setStyleSheet("color: red; font-size: 22px; font-weight: bold; background: #fff0f0; padding: 8px; border-radius: 6px;")
                    QMessageBox.critical(self, "Kết quả phân tích", "⚠️ Email lừa đảo!")
                else:
                    self.result_label.setText("✅ Email bình thường")
                    self.result_label.setStyleSheet("color: green; font-size: 22px; font-weight: bold; background: #f0fff0; padding: 8px; border-radius: 6px;")
                    QMessageBox.information(self, "Kết quả phân tích", "✅ Email bình thường")
            else:
                self.result_label.setText(f"Lỗi: {response.text}")
                self.result_label.setStyleSheet("color: orange;")
                QMessageBox.warning(self, "Kết quả phân tích", f"Lỗi: {response.text}")
        except Exception as e:
            self.result_label.setText(f"Lỗi khi gửi file: {str(e)}")
            self.result_label.setStyleSheet("color: orange;")
            QMessageBox.warning(self, "Kết quả phân tích", f"Lỗi khi gửi file: {str(e)}")

    def refresh_inbox(self):
        """Làm mới hộp thư đến (dùng QThread)"""
        self.loading_label.setText("Đang tải email...")
        self.email_list.clear()
        self.email_loader_thread = EmailLoaderThread(self.email_service)
        self.email_loader_thread.finished.connect(self.on_emails_loaded)
        self.email_loader_thread.error.connect(self.on_emails_error)
        self.email_loader_thread.start()

    def on_emails_loaded(self, emails):
        self.loading_label.setText("")
        for email in emails:
            item = QListWidgetItem(f"{email['subject']} - {email['from']}")
            item.setData(Qt.UserRole, email)
            self.email_list.addItem(item)
        if self.email_list.count() > 0:
            self.email_list.setCurrentRow(0)

    def on_emails_error(self, error_msg):
        self.loading_label.setText("")
        QMessageBox.critical(self, "Lỗi", f"Không thể tải email: {error_msg}")

    def show_email(self, current, previous):
        """Hiển thị nội dung email được chọn"""
        if current is None:
            return
            
        email = current.data(Qt.UserRole)
        
        # Hiển thị thông tin email
        self.email_info.setText(
            f"<b>Tiêu đề:</b> {email['subject']}<br>"
            f"<b>Người gửi:</b> {email['from']}<br>"
            f"<b>Ngày gửi:</b> {email['date']}"
        )
        
        # Hiển thị nội dung
        self.email_body.setText(email['body'])

    def filter_emails(self):
        """Lọc email theo từ khóa tìm kiếm"""
        search_text = self.search_input.text().lower()
        
        for i in range(self.email_list.count()):
            item = self.email_list.item(i)
            email = item.data(Qt.UserRole)
            
            # Kiểm tra từ khóa trong tiêu đề, người gửi và nội dung
            if (search_text in email['subject'].lower() or
                search_text in email['from'].lower() or
                search_text in email['body'].lower()):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def send_email(self):
        """Gửi email"""
        to_addr = self.to_input.text()
        subject = self.subject_input.text()
        body = self.compose_body.toPlainText()
        
        if not to_addr or not subject or not body:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin!")
            return
            
        try:
            # Gửi email
            self.email_service.send_email(to_addr, subject, body)
            
            # Xóa nội dung
            self.to_input.clear()
            self.subject_input.clear()
            self.compose_body.clear()
            
            QMessageBox.information(self, "Thành công", "Email đã được gửi!")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể gửi email: {str(e)}")

    def classify_selected_email(self):
        current_item = self.email_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một email để phân loại!")
            return
        email = current_item.data(Qt.UserRole)
        # Ghép subject + body để phân tích rõ hơn
        content = f"Tiêu đề: {email['subject']}\nNgười gửi: {email['from']}\n\n{email['body']}"
        self.email_input.setPlainText(content)
        self.tab_widget.setCurrentIndex(0)  # Chuyển sang tab phân tích

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ"""
        try:
            self.email_service.close()
        except:
            pass
        event.accept()

    def eventFilter(self, obj, event):
        if obj == self.email_input and event.type() == event.DragEnter:
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if url.toLocalFile().endswith('.eml'):
                        event.accept()
                        return True
            event.ignore()
            return True
        if obj == self.email_input and event.type() == event.Drop:
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith('.eml'):
                    self.load_eml_file(file_path)
            event.accept()
            return True
        return super().eventFilter(obj, event)

    def open_eml_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file .eml", "", "Email Files (*.eml)")
        if file_path:
            self.load_eml_file(file_path)

    def load_eml_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                msg = email.message_from_bytes(f.read())
            subject = msg.get('subject', '')
            from_addr = msg.get('from', '')
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='replace')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='replace')
            content = f"Tiêu đề: {subject}\nNgười gửi: {from_addr}\n\n{body}"
            self.email_input.setPlainText(content)
            self.current_eml_path = file_path
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể đọc file .eml: {str(e)}")
            self.current_eml_path = None

    def logout(self):
        # Xóa file .env nếu có
        try:
            if os.path.exists('.env'):
                os.remove('.env')
        except Exception:
            pass
        self.close()
        # Quay lại màn hình đăng nhập
        from ui.login_dialog import LoginDialog
        login_dialog = LoginDialog()
        if login_dialog.exec_() == LoginDialog.Accepted:
            credentials = login_dialog.get_credentials()
            self.email_service.connect_imap(credentials['email'], credentials['password'])
            self.show() 