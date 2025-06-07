import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from utils.config import (
    GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT,
    GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT
)

class EmailService:
    def __init__(self):
        self.imap_server = None
        self.smtp_server = None
        self.email = None
        self.password = None

    def connect_imap(self, email, password):
        """Kết nối đến máy chủ IMAP"""
        try:
            self.imap_server = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT)
            self.imap_server.login(email, password)
            self.email = email
            self.password = password
            return True
        except Exception as e:
            raise Exception(f"Lỗi kết nối IMAP: {str(e)}")

    def connect_smtp(self):
        """Kết nối đến máy chủ SMTP"""
        try:
            self.smtp_server = smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT)
            self.smtp_server.starttls()
            self.smtp_server.login(self.email, self.password)
            return True
        except Exception as e:
            raise Exception(f"Lỗi kết nối SMTP: {str(e)}")

    def get_emails(self, limit=50):
        """Lấy danh sách email từ hộp thư đến"""
        try:
            self.imap_server.select('INBOX')
            _, messages = self.imap_server.search(None, 'ALL')
            email_ids = messages[0].split()
            
            # Lấy email mới nhất
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            
            emails = []
            for email_id in email_ids:
                _, msg_data = self.imap_server.fetch(email_id, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Lấy thông tin email
                subject = self.decode_email_header(email_message['subject'])
                from_addr = self.decode_email_header(email_message['from'])
                date = email_message['date']
                
                # Lấy nội dung email
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()
                
                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'date': date,
                    'body': body
                })
            
            return emails
        except Exception as e:
            raise Exception(f"Lỗi lấy email: {str(e)}")

    def send_email(self, to_addr, subject, body):
        """Gửi email"""
        try:
            if not self.smtp_server:
                self.connect_smtp()
            
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to_addr
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            self.smtp_server.send_message(msg)
            return True
        except Exception as e:
            raise Exception(f"Lỗi gửi email: {str(e)}")

    def decode_email_header(self, header):
        """Giải mã header email"""
        if header is None:
            return ""
        decoded_header = decode_header(header)
        header_parts = []
        for content, charset in decoded_header:
            if isinstance(content, bytes):
                if charset:
                    header_parts.append(content.decode(charset))
                else:
                    header_parts.append(content.decode())
            else:
                header_parts.append(content)
        return " ".join(header_parts)

    def close(self):
        """Đóng kết nối"""
        if self.imap_server:
            self.imap_server.close()
            self.imap_server.logout()
        if self.smtp_server:
            self.smtp_server.quit() 