import smtplib         #Python built in for sending emails
from email.mime.text import MIMEText    #Python built in for creating emails
from dotenv import load_dotenv
import os
import bcrypt

load_dotenv() #loads the environment variables from the .env file

def send_email(msg):
        with smtplib.SMTP('smtp.office365.com', 587, timeout=10) as server:
            server.starttls()
            server.login(os.getenv("MAIL_ADDRESS"), os.getenv("MAIL_PASSWORD"))
            server.send_message(msg)


def send_recovery_email(email, token):

    base_url = os.getenv("BASE_URL", "http://localhost:5000")
    reset_link = f"{base_url}/reset_password/{token}"

    msg = MIMEText(f"""
    Hello Hornet Helper, 
                   
    We received a request to reset your password. 
                   
    Please click the link below to reset your password:
    {reset_link}

    The link will expire in 1 hour!

    If you did not request a password reset, please ignore this email.
    - The Hornet Helpers Team
    """)
    
    msg['Subject'] = 'Hornet Helpers Password Reset'
    msg['From'] = os.getenv("MAIL_ADDRESS")
    msg['To'] = email

    try:
        send_email(msg)
        print(f"Password reset email successfully sent to {email}")
        return True
    except Exception as e:
        print(f"Error, Failed to send email: {e}")
        return False
    

def send_username_email(email, username):

    msg = MIMEText(f"""
    Hello Hornet Helper, 
                   
    We received a request to recover your username. 
                   
    Your username is: {username}

    If you did not request a username recovery, please ignore this email.
    - The Hornet Helpers Team
    """)
    
    msg['Subject'] = 'Hornet Helpers Username Recovery'
    msg['From'] = os.getenv("MAIL_ADDRESS")
    msg['To'] = email

    try:
        send_email(msg)
        print(f"Username recovery email successfully sent to {email}")
        return True
    except Exception as e:
        print(f"Error, Failed to send email: {e}")
        return False
    
def generate_hashed_password(password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')