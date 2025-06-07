import requests
from utils.config import CLASSIFICATION_KEYWORDS

class ClassificationService:
    def __init__(self):
        self.api_url = 'http://localhost:5000/predict'

    def classify_email(self, email):
        """Phân loại email sử dụng API hoặc từ khóa"""
        try:
            # Thử phân loại qua API
            email_data = {
                'subject': email['subject'],
                'body': email['body'],
                'from': email['from']
            }
            
            response = requests.post(self.api_url, json=email_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('prediction') == 'spam':
                    return "Spam"
                elif result.get('prediction') == 'phishing':
                    return "Phishing"
                else:
                    return "Normal"
            else:
                # Nếu API không hoạt động, sử dụng phân loại đơn giản
                return self.simple_classify(email)
                
        except Exception as e:
            print(f"Lỗi khi gọi API: {str(e)}")
            # Nếu có lỗi, sử dụng phân loại đơn giản
            return self.simple_classify(email)

    def simple_classify(self, email):
        """Phân loại email đơn giản dựa trên từ khóa"""
        subject = email['subject'].lower()
        body = email['body'].lower()
        from_addr = email['from'].lower()
        
        # Kiểm tra các dấu hiệu của email lừa đảo
        for keyword in CLASSIFICATION_KEYWORDS['phishing']:
            if keyword in subject or keyword in body:
                return "Phishing"
        
        # Kiểm tra các dấu hiệu của spam
        for keyword in CLASSIFICATION_KEYWORDS['spam']:
            if keyword in subject or keyword in body:
                return "Spam"
        
        # Kiểm tra địa chỉ người gửi
        suspicious_domains = [
            'free', 'temp', 'mail', 'email', 'random', 'fake',
            'spam', 'trash', 'throwaway', 'disposable', 'temporary'
        ]
        
        for domain in suspicious_domains:
            if domain in from_addr:
                return "Spam"
        
        # Nếu không có dấu hiệu nào, coi là email bình thường
        return "Normal" 