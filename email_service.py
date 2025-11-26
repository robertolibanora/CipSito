import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

# Carica il file .env dalla directory corrente
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

def validate_email(email):
    """Valida il formato dell'email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_contact_email(name, email, phone, message, template_dir=None):
    """Invia un'email di notifica HTML quando arriva un nuovo messaggio di contatto"""
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port_str = os.environ.get('SMTP_PORT')
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    recipient_email = os.environ.get('RECIPIENT_EMAIL')
    
    # Verifica configurazione
    if not all([smtp_server, smtp_port_str, smtp_username, smtp_password, recipient_email]):
        missing = []
        if not smtp_server: missing.append('SMTP_SERVER')
        if not smtp_port_str: missing.append('SMTP_PORT')
        if not smtp_username: missing.append('SMTP_USERNAME')
        if not smtp_password: missing.append('SMTP_PASSWORD')
        if not recipient_email: missing.append('RECIPIENT_EMAIL')
        error_msg = f"Configurazione SMTP incompleta. Variabili mancanti: {', '.join(missing)}"
        print(f"❌ {error_msg}")
        return False
    
    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        error_msg = f"SMTP_PORT deve essere un numero valido. Valore ricevuto: {smtp_port_str}"
        print(f"❌ {error_msg}")
        return False
    
    try:
        print(f"📧 Tentativo invio email a {recipient_email} via {smtp_server}:{smtp_port}")
        
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_username
        msg['To'] = recipient_email
        msg['Subject'] = f'Nuovo messaggio di contatto da {name}'
        msg['Reply-To'] = email
        
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        # Carica il template HTML
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('email_contact.html')
        
        html_body = template.render(
            name=name,
            email=email,
            phone=phone,
            message=message,
            timestamp=timestamp
        )
        
        phone_info = f"Telefono: {phone}\n" if phone else ""
        text_body = f"""
Hai ricevuto un nuovo messaggio dal form di contatto del portfolio.

Dettagli:
---------
Nome: {name}
Email: {email}
{phone_info}Data/Ora: {timestamp}

Messaggio:
----------
{message}

---
Puoi rispondere direttamente a questa email per contattare {name} all'indirizzo: {email}
"""
        
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Connessione SMTP con timeout
        print(f"🔌 Connessione a {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        
        print("🔐 Avvio TLS...")
        server.starttls()
        
        print(f"🔑 Login con {smtp_username}...")
        server.login(smtp_username, smtp_password)
        
        print("📤 Invio messaggio...")
        server.send_message(msg)
        
        print("🔌 Chiusura connessione...")
        server.quit()
        
        print(f"✅ Email inviata con successo a {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Errore autenticazione SMTP: {str(e)}\n💡 Per Gmail, usa una 'App Password' invece della password normale. Vai su: https://myaccount.google.com/apppasswords"
        print(f"❌ {error_msg}")
        return False
    except smtplib.SMTPException as e:
        error_msg = f"Errore SMTP: {str(e)}"
        print(f"❌ {error_msg}")
        return False
    except ConnectionRefusedError:
        error_msg = f"Connessione rifiutata. Verifica che {smtp_server}:{smtp_port} sia corretto."
        print(f"❌ {error_msg}")
        return False
    except TimeoutError:
        error_msg = f"Timeout nella connessione a {smtp_server}:{smtp_port}. Verifica la connessione internet."
        print(f"❌ {error_msg}")
        return False
    except Exception as e:
        error_msg = f"Errore generico nell'invio dell'email: {type(e).__name__}: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(traceback.format_exc())
        return False

