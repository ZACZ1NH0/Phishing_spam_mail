# Phishing Email Classifier API

Simple Flask REST API để phân loại email thành **Normal** hoặc **Phishing** dùng model đã train sẵn.

## Cấu trúc file

- `app.py`: Flask app chạy API `/predict`, nhận file `.eml` qua POST request.
- `test_request.py`: Script test API với file `.eml`.
- `email1.eml`, `email2.eml`: File email mẫu để test.

## Link tải model (file lớn, tải về rồi đặt cùng thư mục với `api.py`)

https://drive.google.com/drive/folders/1q5z5_Uj48GuXP8WcXXQpQSTPnnqNFxG5?usp=sharing

## Cài đặt
```bash
cd model
```

```bash
python api.py
```

sửa đường dẫn file email trong test_request.py 
```
files = {'file': open('./email/email1.eml', 'rb')}  # file .eml bạn muốn test
```

```bash
python test_request.py
```

```Kết quả trả về có form như sau:
{
  "subject": ,
  "body": ,
  "prediction": ,
  "saved_path": 
}
```
file .eml thuộc email rác hoặc phishing sẽ được phân vào folder phishing_emails
file .eml thuộc email bình thường sẽ được phân vào folder normal_emails
