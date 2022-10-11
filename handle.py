
from gevent import monkey

monkey.patch_all()


from flask import Flask
from flask import render_template, request
from gevent.pywsgi import WSGIServer
from flask_compress import Compress
from os import mkdir
from werkzeug.utils import secure_filename

# Imports for Email
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Imports for threading
from threading import Thread


# -------------------------
# Function to send the emails 

#NOTES:
# Is there a way to set the 'reply to' ?
#      --> want to set the confirmation message's reply to to the bakery
#      --> want to set the notification message's reply to to the customer
# ** Want to move to a separate file but need to mess with the imports . . . this works for now

def send_emails(customer_name, customer_email, order_date):
    # General constants
    port = 465
    password = '' # redacted
    smtp_server = '' # redacted
    sender_email = "" # redacted

    # Confirmation message to the customer
    conf_message = MIMEMultipart('alternative')
    conf_message['Subject'] = 'Order Inquiry Confirmation'
    conf_message['From'] = "Josie's Bakery"
    conf_message['To'] = customer_email

    conf_text = """\
        Hello {},
        
        We have received your order for {}. Please allow us up to two (2) days to process your order, then we will be in touch!
        If you have any additional questions or haven't heard from us in a few days, please don't hesistate to reach out.
        

        Best,
        
        The Josie's Bakery Team """.format(customer_name, order_date)

    #Turn these into plain/html MIMEText objects
    conf_part1 = MIMEText(conf_text, 'plain')

    # Add HTML/plain-text parts to MIMEMultipart message
    # Note: Email client tries to render the last part first
    #       --> The html version is preferred, so try that first
    #       --> Otherwise the text version will do, so try that second
    conf_message.attach(conf_part1)


    # ---------- + ---------- #


    # Notification message to the bakery
    bakery_email = '' # redacted
    notif_message = MIMEMultipart('alternative')
    notif_message['Subject'] = 'New Custom Order Inquiry' # Include customers name & date here?
    notif_message['From'] = customer_email # Use the receiver's email (the customer's email)
    notif_message['To'] = bakery_email # Use the bakery's actual email

    notif_html = """\
        <html>
            <body>
                <p>{} submitted an order inquiry for {}<br>
                [order details . . .]<br>
                </p>
            </body>
        </html>
    """.format(customer_name, order_date)
    

    #Turn these into plain/html MIMEText objects
    notif_part1 = MIMEText(notif_html, 'html')

    # Add HTML/plain-text parts to MIMEMultipart message
    # Note: Email client tries to render the last part first
    #       --> The html version is preferred, so try that first
    #       --> Otherwise the text version will do, so try that second
    notif_message.attach(notif_part1)

    # Create a secure connection with server and send BOTH emails
    #   --> more efficient than logging in twice
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, customer_email, conf_message.as_string())
        server.sendmail(sender_email, bakery_email, notif_message.as_string())
    print('Emails sent.')

#----------------------------
# Code for handling server requests

app = Flask(__name__)

compress = Compress()
compress.init_app(app)


# Rendering the home page with the form
@app.route('/')
def index():
    return render_template('index.html')

# Rendering the post-submission page
@app.route('/received', methods=['POST'])
def submission():
    loi = request.files.getlist('imgs')
    cust_fName = request.form.get('firstName')
    cust_lName = request.form.get('lastName')
    order_date = request.form.get('dateInput')
    pathExt = f'/{cust_fName}-{cust_lName}_{order_date}'

    mkdir(f'./forms/{pathExt}') # Make a directory to store the order details and reference images in one place
    thisFormTxt = open(f'./forms/{pathExt}/order-details.txt', 'w') # Create a text file with the order details 
    loe = request.form

    # Create a thread to send the emails, allowing the page to render while this is going on
    #   so the customer doesn't have to wait 
    t1 = Thread(target=send_emails, args=(f'{cust_fName} {cust_lName}', request.form.get('emailInput'), order_date))
    t1.start()

    # Write to the text file with the relevant order details
    for e in loe: 
        v = request.form.get(e)
        if v != '':
            thisFormTxt.write(f'{e} : {request.form.get(e)}\n')      

    # Save the reference images, if applicable
    thisFormTxt.write(f'number of files: {len(loi)}')
    print(f'Saving {len(loi)} images . . . ')
    for i in loi:
        i.save(f'./forms/{pathExt}/{secure_filename(i.filename)}')

    print('Rendering template')
    return render_template('submission-received.html')
    


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()
