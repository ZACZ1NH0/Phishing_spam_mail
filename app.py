import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QTextEdit, 
                            QMessageBox, QProgressBar, QHBoxLayout, QLineEdit,
                            QComboBox, QListWidget, QSplitter, QTabWidget,
                            QDialog, QFormLayout, QCheckBox, QGroupBox, QListWidgetItem,
                            QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
import requests
import json
import logging
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import os
from dotenv import load_dotenv, set_key

# Load environment variables
load_dotenv()

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        # Email input
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        layout.addRow("Email:", self.email_input)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Password:", self.password_input)
        
        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember me")
        layout.addRow("", self.remember_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)
        layout.addRow("", button_layout)
        
        # Load saved credentials if they exist
        saved_email = os.getenv('SAVED_EMAIL')
        if saved_email:
            self.email_input.setText(saved_email)
            self.remember_checkbox.setChecked(True)

    def get_credentials(self):
        return {
            'email': self.email_input.text(),
            'password': self.password_input.text(),
            'remember': self.remember_checkbox.isChecked()
        }

class EmailAnalyzerThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            with open(self.file_path, 'rb') as f:
                files = {'file': f}
                logger.debug(f"Sending request to API with file: {self.file_path}")
                response = requests.post('http://localhost:5000/predict', files=files)
                
                logger.debug(f"Response status code: {response.status_code}")
                logger.debug(f"Response content: {response.text}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        self.finished.emit(result)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {str(e)}")
                        self.error.emit(f"Error parsing response: {str(e)}")
                else:
                    error_msg = "Unknown error"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', error_msg)
                    except:
                        error_msg = response.text
                    self.error.emit(f"Error: {error_msg}")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error - API server might not be running")
            self.error.emit("Cannot connect to API server. Please make sure the server is running.")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self.error.emit(str(e))

class EmailReceiverThread(QThread):
    emails_received = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, email_address, password, imap_server):
        super().__init__()
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server

    def run(self):
        try:
            self.progress.emit("Đang kết nối đến máy chủ email...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            
            self.progress.emit("Đang đăng nhập...")
            mail.login(self.email_address, self.password)
            
            self.progress.emit("Đang truy cập hộp thư đến...")
            mail.select('inbox')
            
            self.progress.emit("Đang tải danh sách email...")
            _, messages = mail.search(None, 'ALL')
            email_list = []
            
            message_numbers = messages[0].split()
            total_messages = len(message_numbers)
            self.progress.emit(f"Tìm thấy {total_messages} email")
            
            # Lấy 50 email mới nhất
            start_idx = max(0, total_messages - 50)
            
            for i in range(start_idx, total_messages):
                num = message_numbers[i]
                self.progress.emit(f"Đang tải email {i+1}/{total_messages}...")
                
                try:
                    _, msg = mail.fetch(num, '(RFC822)')
                    email_body = msg[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    subject = email_message['subject']
                    from_addr = email_message['from']
                    date = email_message['date']
                    
                    # Lấy nội dung email
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                except:
                                    body = part.get_payload()
                                break
                    else:
                        try:
                            body = email_message.get_payload(decode=True).decode()
                        except:
                            body = email_message.get_payload()
                    
                    email_list.append({
                        'subject': subject,
                        'from': from_addr,
                        'date': date,
                        'body': body
                    })
                except Exception as e:
                    self.progress.emit(f"Bỏ qua email lỗi: {str(e)}")
                    continue
            
            # Sắp xếp email theo thời gian (mới nhất lên đầu)
            email_list.sort(key=lambda x: email.utils.parsedate_to_datetime(x['date']), reverse=True)
            
            self.progress.emit(f"Đã tải xong {len(email_list)} email")
            self.emails_received.emit(email_list)
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            try:
                mail.logout()
            except:
                pass

    def update_email_list(self, emails):
        self.email_list.clear()
        self.status_label.setText(f"Đã tải {len(emails)} email")
        
        if not emails:
            self.email_list.addItem("Không tìm thấy email nào")
            return
            
        for email in emails:
            try:
                # Format hiển thị email
                display_text = f"📧 {email['subject']}\n"
                display_text += f"👤 Từ: {email['from']}\n"
                display_text += f"🕒 {email['date']}"
                
                item = QListWidgetItem(display_text)
                self.email_list.addItem(item)
            except:
                continue
        
        self.email_list.setProperty('emails', emails)
        
        # Tự động chọn email đầu tiên
        if self.email_list.count() > 0:
            self.email_list.setCurrentRow(0)
            self.show_email_details(self.email_list.item(0))

    def show_email_details(self, item):
        if not item:
            return
            
        emails = self.email_list.property('emails')
        if not emails:
            return
            
        index = self.email_list.row(item)
        if index < 0 or index >= len(emails):
            return
            
        email = emails[index]
        
        # Hiển thị chi tiết email
        details = f"Tiêu đề: {email['subject']}\n"
        details += f"Người gửi: {email['from']}\n"
        details += f"Ngày: {email['date']}\n"
        details += f"\nNội dung:\n{email['body']}"
        
        self.email_details.setPlainText(details)

class EmailSenderThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, to_email, subject, body, smtp_server, smtp_port, email_address, password):
        super().__init__()
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_address = email_address
        self.password = password

    def run(self):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = self.to_email
            msg['Subject'] = self.subject
            
            msg.attach(MIMEText(self.body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.password)
            server.send_message(msg)
            server.quit()
            
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class GmailGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hướng dẫn cài đặt Gmail")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # Tạo scroll area để chứa nội dung
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Tiêu đề
        title = QLabel("Hướng dẫn cài đặt Gmail cho ứng dụng")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        content_layout.addWidget(title)
        
        # Bước 1: Bật Xác minh 2 bước
        step1 = QLabel("Bước 1: Bật Xác minh 2 bước")
        step1.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        content_layout.addWidget(step1)
        
        step1_content = QLabel(
            "1. Đăng nhập vào tài khoản Google của bạn\n"
            "2. Truy cập: https://myaccount.google.com/security\n"
            "3. Tìm mục 'Xác minh 2 bước' (2-Step Verification)\n"
            "4. Nhấn 'Bắt đầu' và làm theo hướng dẫn\n"
            "5. Xác nhận số điện thoại của bạn\n"
            "6. Hoàn tất quá trình xác minh"
        )
        step1_content.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(step1_content)
        
        # Bước 2: Tạo App Password
        step2 = QLabel("Bước 2: Tạo App Password")
        step2.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        content_layout.addWidget(step2)
        
        step2_content = QLabel(
            "1. Sau khi bật Xác minh 2 bước, quay lại trang Bảo mật\n"
            "2. Tìm mục 'Mật khẩu ứng dụng' (App Passwords)\n"
            "3. Chọn 'Ứng dụng khác' (Other)\n"
            "4. Đặt tên cho ứng dụng (ví dụ: 'Email App')\n"
            "5. Nhấn 'Tạo' (Generate)\n"
            "6. Google sẽ tạo cho bạn một mật khẩu 16 ký tự\n"
            "7. Sao chép mật khẩu này và lưu lại cẩn thận"
        )
        step2_content.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(step2_content)
        
        # Bước 3: Sử dụng App Password
        step3 = QLabel("Bước 3: Sử dụng App Password")
        step3.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        content_layout.addWidget(step3)
        
        step3_content = QLabel(
            "1. Mở ứng dụng của chúng ta\n"
            "2. Đăng nhập với:\n"
            "   - Email: địa chỉ Gmail của bạn\n"
            "   - Mật khẩu: App Password 16 ký tự vừa tạo\n"
            "3. Không cần nhập dấu cách trong App Password"
        )
        step3_content.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(step3_content)
        
        # Lưu ý quan trọng
        notes = QLabel("Lưu ý quan trọng:")
        notes.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px; color: red;")
        content_layout.addWidget(notes)
        
        notes_content = QLabel(
            "• App Password chỉ hiển thị một lần khi tạo, hãy lưu lại cẩn thận\n"
            "• Bạn có thể tạo nhiều App Password cho nhiều ứng dụng khác nhau\n"
            "• Nếu quên hoặc mất App Password, bạn có thể xóa và tạo mới\n"
            "• App Password an toàn hơn vì nó chỉ có quyền truy cập email"
        )
        notes_content.setStyleSheet("margin-left: 20px; color: red;")
        content_layout.addWidget(notes_content)
        
        # Thêm nút đóng
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.accept)
        content_layout.addWidget(close_button)
        
        # Thêm content vào scroll area
        scroll.setWidget(content)
        layout.addWidget(scroll)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Email Analyzer")
        self.setMinimumSize(800, 600)
        
        # Khởi tạo các biến
        self.current_email = None
        self.current_password = None
        
        # Tạo giao diện chính
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Tạo các input field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Nhập email của bạn")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Nhập mật khẩu")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Tạo nút đăng nhập và hướng dẫn
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Đăng nhập")
        self.login_button.clicked.connect(self.check_login)
        self.guide_button = QPushButton("Hướng dẫn Gmail")
        self.guide_button.clicked.connect(self.show_gmail_guide)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.guide_button)
        self.layout.addLayout(button_layout)
        
        # Thêm các widget vào layout
        self.layout.addWidget(QLabel("Email:"))
        self.layout.addWidget(self.email_input)
        self.layout.addWidget(QLabel("Mật khẩu:"))
        self.layout.addWidget(self.password_input)
        self.layout.addLayout(button_layout)
        
        # Tạo tab widget
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Kiểm tra đăng nhập
        self.check_login()
        
    def show_gmail_guide(self):
        msg = QMessageBox()
        msg.setWindowTitle("Hướng dẫn cài đặt Gmail")
        msg.setText("Hướng dẫn chi tiết cách tạo và sử dụng App Password cho Gmail")
        msg.setDetailedText(
            "Bước 1: Bật Xác minh 2 bước\n"
            "1. Đăng nhập vào tài khoản Google của bạn\n"
            "2. Truy cập: https://myaccount.google.com/security\n"
            "3. Tìm mục 'Xác minh 2 bước' (2-Step Verification)\n"
            "4. Nhấn 'Bắt đầu' và làm theo hướng dẫn\n"
            "5. Xác nhận số điện thoại của bạn\n"
            "6. Hoàn tất quá trình xác minh\n\n"
            "Bước 2: Tạo App Password\n"
            "1. Sau khi bật Xác minh 2 bước, quay lại trang Bảo mật\n"
            "2. Tìm mục 'Mật khẩu ứng dụng' (App Passwords)\n"
            "3. Chọn 'Ứng dụng khác' (Other)\n"
            "4. Đặt tên cho ứng dụng (ví dụ: 'Email App')\n"
            "5. Nhấn 'Tạo' (Generate)\n"
            "6. Google sẽ tạo cho bạn một mật khẩu 16 ký tự\n"
            "7. Sao chép mật khẩu này và lưu lại cẩn thận\n\n"
            "Bước 3: Sử dụng App Password\n"
            "1. Mở ứng dụng của chúng ta\n"
            "2. Đăng nhập với:\n"
            "   - Email: địa chỉ Gmail của bạn\n"
            "   - Mật khẩu: App Password 16 ký tự vừa tạo\n"
            "3. Không cần nhập dấu cách trong App Password\n\n"
            "Lưu ý quan trọng:\n"
            "• App Password chỉ hiển thị một lần khi tạo, hãy lưu lại cẩn thận\n"
            "• Bạn có thể tạo nhiều App Password cho nhiều ứng dụng khác nhau\n"
            "• Nếu quên hoặc mất App Password, bạn có thể xóa và tạo mới\n"
            "• App Password an toàn hơn vì nó chỉ có quyền truy cập email"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def check_login(self):
        email = self.email_input.text()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ email và mật khẩu")
            return
            
        # Kiểm tra nếu là Gmail
        if "@gmail.com" in email.lower():
            reply = QMessageBox.question(
                self,
                "Thông báo Gmail",
                "Bạn đang sử dụng Gmail. Để sử dụng Gmail, bạn cần:\n\n"
                "1. Bật Xác minh 2 bước\n"
                "2. Tạo App Password\n"
                "3. Sử dụng App Password thay vì mật khẩu thông thường\n\n"
                "Bạn đã thực hiện các bước trên chưa?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                self.show_gmail_guide()
                return

        try:
            # Kiểm tra kết nối với Gmail
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(email, password)
            mail.logout()
            
            # Lưu thông tin đăng nhập
            self.current_email = email
            self.current_password = password
            
            # Xóa các tab cũ
            self.tabs.clear()
            
            # Tạo các tab mới
            self.create_analyzer_tab()
            self.create_inbox_tab()
            self.create_compose_tab()
            
            # Chuyển đến tab inbox
            self.tabs.setCurrentIndex(1)
            
            # Tải email sau 0.5 giây
            QTimer.singleShot(500, self.refresh_inbox)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi đăng nhập",
                f"Không thể đăng nhập: {str(e)}\n\n"
                "Vui lòng kiểm tra:\n"
                "1. Bạn đã bật Xác minh 2 bước chưa?\n"
                "2. Bạn đã tạo App Password chưa?\n"
                "3. Bạn đang sử dụng App Password (không phải mật khẩu Gmail thông thường)"
            )

    def create_inbox_tab(self):
        inbox_tab = QWidget()
        layout = QVBoxLayout(inbox_tab)
        
        # Tạo thanh tìm kiếm
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm email...")
        self.search_input.textChanged.connect(self.filter_emails)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Tạo splitter để chia màn hình
        splitter = QSplitter(Qt.Horizontal)
        
        # Tạo danh sách email
        self.email_list = QListWidget()
        self.email_list.currentItemChanged.connect(self.show_email_details)
        splitter.addWidget(self.email_list)
        
        # Tạo phần hiển thị chi tiết email
        self.email_details = QTextEdit()
        self.email_details.setReadOnly(True)
        splitter.addWidget(self.email_details)
        
        # Thêm splitter vào layout
        layout.addWidget(splitter)
        
        # Thêm tab vào tab widget
        self.tabs.addTab(inbox_tab, "Hộp thư đến")
        
        # Tạo label hiển thị trạng thái
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

    def refresh_inbox(self):
        if not hasattr(self, 'current_email') or not hasattr(self, 'current_password'):
            self.status_label.setText("Vui lòng đăng nhập trước")
            return
            
        self.status_label.setText("Đang tải email...")
        self.email_list.clear()
        self.email_details.clear()
        
        # Luôn sử dụng Gmail IMAP
        imap_server = 'imap.gmail.com'
        
        try:
            # Kiểm tra kết nối trước
            self.status_label.setText("Đang kiểm tra kết nối...")
            mail = imaplib.IMAP4_SSL(imap_server)
            
            # Thử đăng nhập
            self.status_label.setText("Đang đăng nhập...")
            try:
                mail.login(self.current_email, self.current_password)
            except imaplib.IMAP4.error as e:
                error_msg = str(e)
                if "Authentication failed" in error_msg:
                    self.status_label.setText("Lỗi xác thực")
                    QMessageBox.warning(
                        self,
                        "Lỗi đăng nhập",
                        "Không thể đăng nhập vào Gmail.\n\n"
                        "Vui lòng kiểm tra:\n"
                        "1. Bạn đã bật Xác minh 2 bước chưa?\n"
                        "2. Bạn đã tạo App Password chưa?\n"
                        "3. Bạn đang sử dụng App Password (không phải mật khẩu Gmail thông thường)"
                    )
                else:
                    self.status_label.setText(f"Lỗi: {error_msg}")
                return
                
            # Tạo thread để tải email
            self.receiver_thread = EmailReceiverThread(
                self.current_email,
                self.current_password,
                imap_server
            )
            self.receiver_thread.emails_received.connect(self.update_email_list)
            self.receiver_thread.error.connect(self.handle_email_error)
            self.receiver_thread.progress.connect(self.status_label.setText)
            self.receiver_thread.start()
            
        except Exception as e:
            self.status_label.setText(f"Lỗi kết nối: {str(e)}")
            QMessageBox.critical(
                self,
                "Lỗi kết nối",
                f"Không thể kết nối đến Gmail:\n{str(e)}\n\n"
                "Vui lòng kiểm tra:\n"
                "1. Kết nối internet của bạn\n"
                "2. Tài khoản Gmail của bạn đã bật IMAP chưa\n"
                "3. Bạn đã tạo App Password chưa"
            )

    def update_email_list(self, emails):
        self.email_list.clear()
        self.status_label.setText(f"Đã tải {len(emails)} email")
        
        if not emails:
            self.email_list.addItem("Không tìm thấy email nào")
            return
            
        for email in emails:
            try:
                # Format hiển thị email
                display_text = f"📧 {email['subject']}\n"
                display_text += f"👤 Từ: {email['from']}\n"
                display_text += f"🕒 {email['date']}"
                
                item = QListWidgetItem(display_text)
                self.email_list.addItem(item)
            except:
                continue
        
        self.email_list.setProperty('emails', emails)
        
        # Tự động chọn email đầu tiên
        if self.email_list.count() > 0:
            self.email_list.setCurrentRow(0)
            self.show_email_details(self.email_list.item(0))

    def show_email_details(self, item):
        if not item:
            return
            
        emails = self.email_list.property('emails')
        if not emails:
            return
            
        index = self.email_list.row(item)
        if index < 0 or index >= len(emails):
            return
            
        email = emails[index]
        
        # Hiển thị chi tiết email
        details = f"Tiêu đề: {email['subject']}\n"
        details += f"Người gửi: {email['from']}\n"
        details += f"Ngày: {email['date']}\n"
        details += f"\nNội dung:\n{email['body']}"
        
        self.email_details.setPlainText(details)

    def handle_email_error(self, error_msg):
        self.email_list.clear()
        self.status_label.setText("Lỗi tải email")
        
        if "Authentication failed" in error_msg:
            self.email_list.addItem("⚠️ Lỗi xác thực Gmail")
            self.email_list.addItem("Vui lòng làm theo các bước sau:")
            self.email_list.addItem("1. Đăng nhập vào tài khoản Google")
            self.email_list.addItem("2. Vào phần 'Bảo mật'")
            self.email_list.addItem("3. Bật 'Xác minh 2 bước'")
            self.email_list.addItem("4. Tạo 'Mật khẩu ứng dụng'")
            self.email_list.addItem("5. Sử dụng mật khẩu ứng dụng để đăng nhập")
        elif "Connection refused" in error_msg:
            self.email_list.addItem("⚠️ Không thể kết nối đến Gmail")
            self.email_list.addItem("Vui lòng kiểm tra:")
            self.email_list.addItem("1. Kết nối internet của bạn")
            self.email_list.addItem("2. Tài khoản Gmail đã bật IMAP chưa")
        else:
            self.email_list.addItem(f"⚠️ Lỗi: {error_msg}")
            self.email_list.addItem("Vui lòng thử lại sau")

    def filter_emails(self, text):
        for i in range(self.email_list.count()):
            item = self.email_list.item(i)
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def create_analyzer_tab(self):
        analyzer_tab = QWidget()
        layout = QVBoxLayout(analyzer_tab)
        
        # Title
        title = QLabel("Email Phishing Detection")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Upload button
        self.upload_btn = QPushButton("Select Email File (.eml)")
        self.upload_btn.setMinimumHeight(40)
        self.upload_btn.clicked.connect(self.select_file)
        layout.addWidget(self.upload_btn)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Result label
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setFont(QFont('Arial', 12))
        layout.addWidget(self.result_label)
        
        # Email content display
        self.email_content = QTextEdit()
        self.email_content.setReadOnly(True)
        layout.addWidget(self.email_content)
        
        self.tabs.addTab(analyzer_tab, "Analyzer")

    def create_compose_tab(self):
        compose_tab = QWidget()
        layout = QVBoxLayout(compose_tab)
        
        # Email configuration
        config_layout = QHBoxLayout()
        
        self.smtp_email_input = QLineEdit()
        self.smtp_email_input.setPlaceholderText("Your Email")
        config_layout.addWidget(self.smtp_email_input)
        
        self.smtp_password_input = QLineEdit()
        self.smtp_password_input.setPlaceholderText("Password")
        self.smtp_password_input.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.smtp_password_input)
        
        self.smtp_server_input = QLineEdit()
        self.smtp_server_input.setPlaceholderText("SMTP Server (e.g., smtp.gmail.com)")
        config_layout.addWidget(self.smtp_server_input)
        
        self.smtp_port_input = QLineEdit()
        self.smtp_port_input.setPlaceholderText("SMTP Port (e.g., 587)")
        config_layout.addWidget(self.smtp_port_input)
        
        layout.addLayout(config_layout)
        
        # Compose email
        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText("To")
        layout.addWidget(self.to_input)
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Subject")
        layout.addWidget(self.subject_input)
        
        self.compose_body = QTextEdit()
        self.compose_body.setPlaceholderText("Write your email here...")
        layout.addWidget(self.compose_body)
        
        send_btn = QPushButton("Send Email")
        send_btn.clicked.connect(self.send_email)
        layout.addWidget(send_btn)
        
        self.tabs.addTab(compose_tab, "Compose")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Email File",
            "",
            "Email Files (*.eml)"
        )
        
        if file_path:
            self.analyze_email(file_path)

    def analyze_email(self, file_path):
        self.progress.setVisible(True)
        self.upload_btn.setEnabled(False)
        self.result_label.setText("Analyzing email...")
        self.email_content.clear()
        
        self.analyzer_thread = EmailAnalyzerThread(file_path)
        self.analyzer_thread.finished.connect(self.handle_result)
        self.analyzer_thread.error.connect(self.handle_error)
        self.analyzer_thread.start()

    def handle_result(self, result):
        self.progress.setVisible(False)
        self.upload_btn.setEnabled(True)
        
        if result['prediction'] == 'phishing':
            self.result_label.setText("⚠️ This is a phishing email!")
            self.result_label.setStyleSheet("color: #d32f2f;")
        else:
            self.result_label.setText("✓ This is a normal email")
            self.result_label.setStyleSheet("color: #388e3c;")
        
        # Display email content
        content = f"Subject: {result['subject']}\n\n"
        content += f"Body:\n{result['body']}"
        self.email_content.setText(content)

    def handle_error(self, error_msg):
        self.progress.setVisible(False)
        self.upload_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_msg)

    def send_email(self):
        to_email = self.to_input.text()
        subject = self.subject_input.text()
        body = self.compose_body.toPlainText()
        email_address = self.smtp_email_input.text()
        password = self.smtp_password_input.text()
        smtp_server = self.smtp_server_input.text()
        smtp_port = self.smtp_port_input.text()
        
        if not all([to_email, subject, body, email_address, password, smtp_server, smtp_port]):
            QMessageBox.warning(self, "Warning", "Please fill in all fields")
            return
        
        try:
            smtp_port = int(smtp_port)
        except ValueError:
            QMessageBox.warning(self, "Warning", "SMTP port must be a number")
            return
        
        self.sender_thread = EmailSenderThread(
            to_email, subject, body, smtp_server, smtp_port, email_address, password
        )
        self.sender_thread.finished.connect(self.email_sent)
        self.sender_thread.error.connect(self.handle_error)
        self.sender_thread.start()

    def email_sent(self):
        QMessageBox.information(self, "Success", "Email sent successfully!")
        self.to_input.clear()
        self.subject_input.clear()
        self.compose_body.clear()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 