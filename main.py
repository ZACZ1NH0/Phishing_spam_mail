import sys
from PyQt5.QtWidgets import QApplication
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from services.email_service import EmailService
from services.classification_service import ClassificationService

def main():
    app = QApplication(sys.argv)
    
    # Hiển thị màn hình đăng nhập
    login_dialog = LoginDialog()
    if login_dialog.exec_() == LoginDialog.Accepted:
        # Lấy thông tin đăng nhập
        credentials = login_dialog.get_credentials()
        
        # Khởi tạo các service
        email_service = EmailService()
        classification_service = ClassificationService()
        
        # Kết nối email
        email_service.connect_imap(credentials['email'], credentials['password'])
        
        # Khởi tạo và hiển thị cửa sổ chính
        main_window = MainWindow(email_service, classification_service)
        main_window.show()
        
        sys.exit(app.exec_())

if __name__ == '__main__':
    main() 