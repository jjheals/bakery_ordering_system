from gevent import monkey

monkey.patch_all()

from flask import Flask
from flask import render_template, request
from gevent.pywsgi import WSGIServer
from flask_compress import Compress

# Imports for Email
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    password = '' # Redacted
    smtp_server = 'smtp.gmail.com'
    sender_email = '' # Redacted

    # Confirmation message to the customer
    conf_message = MIMEMultipart('alternative')
    conf_message['Subject'] = 'Order Inquiry Confirmation'
    conf_message['From'] = "Josie's Bakery"
    conf_message['To'] = customer_email

    conf_text = """\
        Hello {}, 
        
        We've received your inquiry for {}. Please allow us two (2) days to process
        your order, then a member of our team will be in touch!

        We can't wait to work with you!

        The Josie's Bakery Team
    """.format(customer_name, order_date)

    #Turn these into plain/html MIMEText objects
    conf_part1 = MIMEText(conf_text, 'plain')

    # Add HTML/plain-text parts to MIMEMultipart message
    # Note: Email client tries to render the last part first
    #       --> The customer's email can be formatted with just text, 
    #           no html needed, so cut out the html portion to save
    #           processing time 
    conf_message.attach(conf_part1)


    # ---------- + ---------- #


    # Notification message to the bakery
    bakery_email = '' # Redacted
    notif_message = MIMEMultipart('alternative')
    notif_message['Subject'] = f'New Custom Order Inquiry - For: {order_date} | From: {customer_name} ({customer_email})' 
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
    #       --> We control the access to the email account this is sent to, so 
    #           we know the email client will always render html content and if
    #           it doesn't, we can look up the order and its not a major issue.
    #       --> Cut out the text part to save processing time
    notif_message.attach(notif_part1)

    # Create a secure connection with server and send BOTH emails
    #   --> more efficient than logging in twice
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, customer_email, conf_message.as_string())
        server.sendmail(sender_email, bakery_email, notif_message.as_string())


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
    cust_fName = request.form.get('firstName')
    cust_lName = request.form.get('lastName')
    order_date = request.form.get('dateInput')

    # Create a new file with the order details
    thisFormTxt = open(f'{cust_fName}-{cust_lName}_{order_date}.txt', 'w')
    loe = request.form

    for e in loe: 
        v = request.form.get(e)
        if v != '':
            thisFormTxt.write(f'{e} : {request.form.get(e)}\n')
    
    # Send the respective emails using helper function
    # Note: add error checking here ???
    #   --> If send_emails returns an error, don't render the template and instead
    #       prompt the customer to resubmit the form 
    send_emails(f'/forms/{cust_fName} {cust_lName}', request.form.get('emailInput'), order_date)
    
    # Return and render the submission-received page
    return render_template('submission-received.html')
    


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()
