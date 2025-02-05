import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Email settings
SMTP_SERVER = "smtp.your-email-provider.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@example.com"
SENDER_PASSWORD = "your-email-password"
RECEIVER_EMAIL = "receiver@example.com"

# Create the email
msg = MIMEMultipart()
msg['From'] = SENDER_EMAIL
msg['To'] = RECEIVER_EMAIL
msg['Subject'] = "F5 Load Balancer Backup Files"

# Attach UCS file
ucs_file = 'backup_20230203123456.ucs'
qkview_file = 'qkview_20230203123456.tgz'
vip_file = 'vip_status_20230203123456.json'

# Attach UCS backup file
attach_file = MIMEBase('application', 'octet-stream')
with open(ucs_file, 'rb') as file:
    attach_file.set_payload(file.read())
encoders.encode_base64(attach_file)
attach_file.add_header('Content-Disposition', f'attachment; filename={ucs_file}')
msg.attach(attach_file)

# Attach QKView backup file
attach_file = MIMEBase('application', 'octet-stream')
with open(qkview_file, 'rb') as file:
    attach_file.set_payload(file.read())
encoders.encode_base64(attach_file)
attach_file.add_header('Content-Disposition', f'attachment; filename={qkview_file}')
msg.attach(attach_file)

# Attach VIP status file
attach_file = MIMEBase('application', 'octet-stream')
with open(vip_file, 'rb') as file:
    attach_file.set_payload(file.read())
encoders.encode_base64(attach_file)
attach_file.add_header('Content-Disposition', f'attachment; filename={vip_file}')
msg.attach(attach_file)

# Send email
try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        print("Backup files sent successfully!")
except Exception as e:
    print("Failed to send email:", e)