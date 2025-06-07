from flask import Flask, request, jsonify
from email import policy
from email.parser import BytesParser
import os
from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences
import pickle

app = Flask(__name__)

# Load model đã train 
model = load_model('phishing_email_model.h5')
with open('tokenizer.pkl', 'rb') as f:
    tokenizer = pickle.load(f)

os.makedirs('phishing_emails', exist_ok=True)
os.makedirs('normal_emails', exist_ok=True)

def extract_subject_body(eml_bytes):
    msg = BytesParser(policy=policy.default).parsebytes(eml_bytes)
    subject = msg['subject'] or ''
    # Lấy phần plain text trong body email
    if msg.is_multipart():
        parts = msg.walk()
        body = ''
        for part in parts:
            if part.get_content_type() == 'text/plain':
                body += part.get_content()
    else:
        body = msg.get_content()
    return subject, body

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.endswith('.eml'):
        return jsonify({'error': 'File is not .eml'}), 400

    eml_bytes = file.read()
    subject, body = extract_subject_body(eml_bytes)
    text_combined = subject + ' ' + body
    seq = tokenizer.texts_to_sequences([text_combined])
    padded = pad_sequences(seq, maxlen=255)

    prob = model.predict(padded)[0][0]
    label = 'phishing' if prob >= 0.5 else 'normal_emails'

    # Lưu file vào folder tương ứng
    save_folder = 'phishing_emails' if label == 'phishing' else 'normal_emails'
    filepath = os.path.join(save_folder, file.filename)
    with open(filepath, 'wb') as f:
        f.write(eml_bytes)

    return jsonify({
        'subject': subject,
        'body': body,
        'prediction': label,
        'saved_path': filepath
    })

if __name__ == '__main__':
    app.run(debug=True)
