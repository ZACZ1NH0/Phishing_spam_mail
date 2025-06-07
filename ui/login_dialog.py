from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from services.email_service import EmailService
import os
from utils.config import EMAIL, PASSWORD

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.email_service = EmailService()
        self.init_ui()

    def init_ui(self):
        """Khởi tạo giao diện đăng nhập"""
        self.setWindowTitle("Đăng nhập")
        self.setFixedSize(400, 200)
        
        # Layout chính
        layout = QVBoxLayout()
        
        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setText(EMAIL)
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)
        
        # Mật khẩu
        password_layout = QHBoxLayout()
        password_label = QLabel("Mật khẩu:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText(PASSWORD)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # Nút đăng nhập
        login_button = QPushButton("Đăng nhập")
        login_button.clicked.connect(self.check_login)
        layout.addWidget(login_button)
        
        # Nút hướng dẫn Gmail
        gmail_guide_button = QPushButton("Hướng dẫn đăng nhập Gmail")
        gmail_guide_button.clicked.connect(self.show_gmail_guide)
        layout.addWidget(gmail_guide_button)
        
        self.setLayout(layout)

    def check_login(self):
        """Kiểm tra đăng nhập"""
        email = self.email_input.text()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ email và mật khẩu!")
            return
            
        try:
            # Thử kết nối với Gmail
            self.email_service.connect_imap(email, password)
            # Lưu lại vào .env
            with open('.env', 'w') as f:
                f.write(f'EMAIL={email}\n')
                f.write(f'PASSWORD={password}\n')
            self.accept()  # Đóng dialog nếu đăng nhập thành công
            
        except Exception as e:
            error_msg = str(e)
            if 'Invalid credentials' in error_msg or 'Authentication failed' in error_msg:
                QMessageBox.warning(self, "Lỗi đăng nhập", 
                    "Mật khẩu không đúng. Nếu bạn đang sử dụng Gmail, hãy đảm bảo:\n\n"
                    "1. Bạn đã bật xác thực 2 bước\n"
                    "2. Bạn đang sử dụng Mật khẩu ứng dụng (App Password)\n\n"
                    "Nhấn OK để xem hướng dẫn tạo Mật khẩu ứng dụng.")
                self.show_gmail_guide()
            else:
                QMessageBox.critical(self, "Lỗi", f"Không thể kết nối đến máy chủ email: {error_msg}")

    def show_gmail_guide(self):
        """Hiển thị hướng dẫn tạo Mật khẩu ứng dụng Gmail"""
        guide = """
        Hướng dẫn tạo Mật khẩu ứng dụng Gmail:

        1. Truy cập https://myaccount.google.com/security
        2. Đăng nhập vào tài khoản Gmail của bạn
        3. Tìm và bật "Xác minh 2 bước" nếu chưa bật
        4. Sau khi bật xác minh 2 bước, quay lại trang bảo mật
        5. Tìm "Mật khẩu ứng dụng" (App passwords)
        6. Chọn "Ứng dụng khác" và đặt tên (ví dụ: "Email Client")
        7. Nhấn "Tạo"
        8. Google sẽ hiển thị mật khẩu 16 ký tự
        9. Sao chép mật khẩu này và dán vào ô mật khẩu khi đăng nhập

        Lưu ý: Mật khẩu ứng dụng chỉ hiển thị một lần, hãy lưu lại cẩn thận.
        """
        QMessageBox.information(self, "Hướng dẫn Gmail", guide)

    def get_credentials(self):
        """Lấy thông tin đăng nhập"""
        return {
            'email': self.email_input.text(),
            'password': self.password_input.text()
        } 