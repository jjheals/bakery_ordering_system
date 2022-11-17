
from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask import render_template, request
from gevent.pywsgi import WSGIServer
from flask_compress import Compress
from os import mkdir
from werkzeug.utils import secure_filename

# Imports for Email
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

# Imports for threading
from threading import Thread

# ---------------------------------------------------------------------------------#
# Function to send the emails 

#NOTES:
# Is there a way to set the 'reply to' ?
#      --> want to set the confirmation message's reply to to the bakery
#      --> want to set the notification message's reply to to the customer
# ** Want to move to a separate file but need to mess with the imports . . . this works for now

def send_emails(customer_name, customer_email, customer_phone, order_date,
                folderPath, images):

    print('sending emails ...')
    # General constants
    port = 0
    password = '' # Redacted 
    smtp_server = '' # Redacted
    sender_email = '' # Redacted

    # ---------- + ---------- #
    # Confirmation message to the customer

    conf_message = EmailMessage()
    conf_message['Subject'] = 'Order Inquiry Confirmation'
    conf_message['From'] = "Josie's Bakery"
    conf_message['To'] = customer_email
    conf_message.set_content(
        f"Hello {customer_name},\n\nWe have received your order inquiry for {order_date}! Please allow us up to two days to process your order, a member of our team will call you to confirm your order and collect pre-payment.\n\nBest,\nThe Josie's Bakery Team"
    )

    orderDetails = open(f'{folderPath}/order-details.txt').read().splitlines()
    formatOrderDetails = ''

    print('Formatting order details . . .')

    for line in orderDetails:
        print(f'\n{line}')
        formatOrderDetails += f'<br>{line}'

    # ---------- + ---------- #
    # Notification message to the bakery
    bakery_email = ''  # Redacted

    prim_notif_msg = MIMEMultipart('related')
    prim_notif_msg["From"] = customer_email
    prim_notif_msg["Subject"] = f"New Order Inquiry from {customer_name} ({order_date})"
    prim_notif_msg["To"] = bakery_email

    alt_notif_msg = MIMEMultipart('alternative')
    prim_notif_msg.attach(alt_notif_msg)

    alt_text = MIMEText(f"{customer_name} ({customer_email}, {customer_phone}) \
                has submitted a new order for {order_date}.\n\nOrder details:\n{formatOrderDetails}")
    alt_notif_msg.attach(alt_text)

    images_html = ''

    #Attach Images 
    i=1
    for path in images:
        fp = open(path, 'rb') #Read image 
        img = MIMEImage(fp.read())
        fp.close()

        # Define the image's ID as referenced above
        img.add_header('Content-ID', f'<image{i}>')
        prim_notif_msg.attach(img)

        images_html += f'<br><img src="cid:image{i}"><br><br>'
        i+=1
        
    alt_html = MIMEText(f'{customer_name} ({customer_email}, {customer_phone}) \
                        has submitted a new order for {order_date}.\n\nOrder details:\n{formatOrderDetails}\
                        <br><br>{images_html}>', 'html')
    alt_notif_msg.attach(alt_html)

    # ---------- + ---------- #
    # Sending both emails
    with smtplib.SMTP_SSL(smtp_server, port) as smtp:
        smtp.login(sender_email, password)
        smtp.sendmail(sender_email, bakery_email, prim_notif_msg.as_string())
        print('Notification message sent.')
        smtp.send_message(conf_message)
        print('Confirmation message sent.')
        smtp.close()

#------------------------------------------------------------------------------------#
# Code for handling server requests

app = Flask(__name__)

compress = Compress()
compress.init_app(app)

# ---------- + ---------- #
# Rendering the home page with the form
@app.route('/')
def index():
    return render_template('index.html', errorStatus = 'hidden')


# ---------- + ---------- #
# Rendering the post-submission page
@app.route('/received', methods=['POST'])
def submission():
    loi = request.files.getlist('Images')
    cust_fName = request.form.get('First Name').strip()
    cust_lName = request.form.get('Last Name').strip()
    order_date = request.form.get('Date')
    pathExt = f'{cust_fName}-{cust_lName}_{order_date}'
    
    try:
        mkdir(f'./forms/{pathExt}') # Make a directory to store the order details and reference images in one place
        thisFormTxt = open(f'./forms/{pathExt}/order-details.txt', 'w+') # Create a text file with the order details 
        loe = request.form
        seen = []
        
        # Write to the text file with the relevant order details
        thisFormTxt.write('\n-- CONTACT INFO --\n')
        for e in loe: 
            v = request.form.get(e)
            if v != '' and e != 'Policy Agreement' and (not 'Order' in e):
                if ('Cake' in e) and (not 'Cake' in seen):
                    thisFormTxt.write('\n-- CAKE INFO --\n')
                    seen.append('Cake')
                if ('Cupcakes' in e) and (not 'Cupcakes' in seen):
                    thisFormTxt.write('\n-- CUPCAKE INFO --\n')
                    seen.append('Cupcakes')
                if ('Platter' in e) and (not 'Platter' in seen):
                    thisFormTxt.write('\n-- PLATTER INFO --\n')
                    seen.append('Platter')
                if e == 'Pastries':
                    thisFormTxt.write('\n-- PASTRY INFO --\n')
                if 'Description' in e:
                    thisFormTxt.write('\n\n')
                    
                thisFormTxt.write(f'{e} : {v}\n')
                    
        thisFormTxt.write(f'\nNumber of files: {len(loi)}') 
        thisFormTxt.close()
        
        # Save the reference images, if applicable
        image_paths = []
        print(f'Saving {len(loi)} images . . . ')
        for i in loi:
            i.save(f'./forms/{pathExt}/{secure_filename(i.filename)}')
            image_paths.append(f'./forms/{pathExt}/{secure_filename(i.filename)}')

        # Create a thread to send the emails, allowing the page to render while this is going on
        #   so the customer doesn't have to wait 
        t1 = Thread(target=send_emails, args=(f'{cust_fName} {cust_lName}', request.form.get('Email'), 
                                              request.form.get('Phone Number'), order_date, f'./forms/{pathExt}', 
                                              image_paths))
        t1.start()
        
        print('Rendering template')
        return render_template('submission-received.html')

    except FileExistsError:
        print(
            f'Error: Order for {cust_fName} {cust_lName} on {order_date} already exists'
        )
        return render_template('index.html', errorStatus='flex')
    
    



# ---------- + ---------- #
if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()
