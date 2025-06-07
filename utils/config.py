import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email configuration
EMAIL = os.getenv('EMAIL', '')
PASSWORD = os.getenv('PASSWORD', '')

# Gmail IMAP settings
GMAIL_IMAP_SERVER = 'imap.gmail.com'
GMAIL_IMAP_PORT = 993

# Gmail SMTP settings
GMAIL_SMTP_SERVER = 'smtp.gmail.com'
GMAIL_SMTP_PORT = 587

# Application settings
APP_NAME = "Phishing Email Detector"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Email classification settings
CLASSIFICATION_KEYWORDS = {
    'phishing': [
        'urgent', 'immediate', 'action required', 'verify', 'confirm',
        'account suspended', 'security alert', 'password expired',
        'unusual activity', 'login now', 'click here', 'verify now',
        'confirm your account', 'verify your identity', 'security check',
        'account verification', 'suspicious activity', 'unusual login',
        'password reset', 'account locked', 'verify your email',
        'confirm your email', 'verify your account', 'security verification',
        'account security', 'verify your identity', 'security check',
        'unusual activity', 'verify your account', 'confirm your account'
    ],
    'spam': [
        'lottery', 'winner', 'prize', 'congratulations', 'free',
        'discount', 'offer', 'limited time', 'special offer',
        'exclusive deal', 'save money', 'earn money', 'make money',
        'work from home', 'investment', 'bitcoin', 'crypto',
        'forex', 'trading', 'investment opportunity', 'get rich',
        'quick money', 'easy money', 'make money fast', 'earn fast',
        'quick cash', 'easy cash', 'get paid', 'earn cash',
        'make cash', 'quick income', 'easy income', 'get income'
    ]
} 