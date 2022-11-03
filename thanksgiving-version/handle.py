
from gevent import monkey

monkey.patch_all()

from flask import Flask
from flask import render_template, request
from gevent.pywsgi import WSGIServer
from flask_compress import Compress
from os import mkdir, environ

# Imports for Email
import smtplib
from email.message import EmailMessage

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
                folderPath, customer_total):
    # General constants
    port = 465
    password = '' # Redacted
    smtp_server = '' # Redacted
    sender_email = '' # Redacted

    if order_date == 'Tuesday': order_date = 'Tuesday 11/22/2022'
    else: order_date = 'Wednesday 11/23/2022'
    
    # ---------- + ---------- #
    # Confirmation message to the customer

    conf_message = EmailMessage()
    conf_message['Subject'] = 'Order Inquiry Confirmation'
    conf_message['From'] = "Josie's Bakery"
    conf_message['To'] = customer_email
    conf_message.set_content(
        f"Hello {customer_name},\n\nWe have received your Thanksgiving order for {order_date}! Please allow us up to two days to process your order, a member of our team will call you to confirm your order and collect pre-payment (${customer_total}).\n\nBest,\nThe Josie's Bakery Team"
    )

    orderDetails = open(f'{folderPath}/order-details.txt').read().splitlines()

    formatOrderDetails = ''

    print('Formatting order details . . .')

    for line in orderDetails:
        formatOrderDetails += f'\n{line}'
        
    # ---------- + ---------- #
    # Notification message to the bakery
    bakery_email = '' # Redacted

    notif_msg = EmailMessage()
    notif_msg["From"] = customer_email
    notif_msg[
        "Subject"] = f"New Thanksgiving Order Inquiry from {customer_name}"
    notif_msg["To"] = bakery_email
    notif_msg.set_content(
        f"{customer_name} ({customer_email}, {customer_phone}) has submitted a new Thanksgiving order for {order_date}.\n\nOrder details:\n{formatOrderDetails}"
    )

    with smtplib.SMTP_SSL(smtp_server, port) as smtp:
        smtp.login(sender_email, password)
        smtp.send_message(notif_msg)
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
    return render_template('index.html', errorStatus='hidden')


# ---------- + ---------- #
# Rendering the post-submission page
@app.route('/received', methods=['POST'])
def submission():
    cust_fName = request.form.get('First Name')
    cust_lName = request.form.get('Last Name')
    order_date = request.form.get('Date')
    pathExt = f'/{order_date}/{cust_fName}-{cust_lName}_{order_date}'
    cust_total = 0

    try:
        mkdir(
            f'./forms/{pathExt}'
        )  # Make a directory to store the order details and reference images in one place
        thisFormTxt = open(f'./forms{pathExt}/order-details.txt',
                           'w+')  # Create a text file with the order details

        loe = request.form
        seen = []
        menuItems = {
            'Apple Pie':20, 
            'Pumpkin Pie':20,
            'Pecan Pie':20, 
            'Chocolate Cream Pie':22,
            'Carrot Cake':35, 
            'Spice Cake':35, 
            'Pumpkin Cheesecake':40,
            'Apple Crisp Cheesecake':42,
            'DOZEN Cinnamon Rolls':30, 
            'HALF-DOZEN Cinnamon Rolls':15,
            'Sm. Pastry Platter':50, 
            'Med. Pastry Platter':65, 
            'Lg. Pastry Platter':80, 
            'Sm. Cookie Platter':45, 
            'Med. Cookie Platter':60, 
            'Lg. Cookie Platter':75,
            'Sugar Cookie Kit':15
            }

        # Write to the text file with the relevant order details
        thisFormTxt.write('\n-- CONTACT INFO --\n')
        for e in loe:
            v = request.form.get(e)
            print(v)
            if v != '' and v!= '0' and e != 'Policy Agreement' and (not 'Order' in e):
                if e == 'Allergies':
                    thisFormTxt.write('\n-- ALLERGY INFORMATION --\n')
                    thisFormTxt.write(
                        f'ALLERGY : {request.form.get("Allergies Description")}\n')
                elif (not 'Allergies' in e):
                    if ('Platter' in e) and (not 'Platter' in seen):
                        thisFormTxt.write('\n-- PLATTER INFO --\n')
                        seen.append('Platter')
                    elif (e in menuItems) and (not 'Main' in seen):
                        thisFormTxt.write('\n-- MAIN MENU INFO --\n')
                        seen.append('Main')

                    thisFormTxt.write(f'{e} : {v}\n')

                    if e in menuItems:
                        cust_total+=menuItems[e]

        thisFormTxt.write(f'\n\nCUSTOMER TOTAL: ${cust_total}')
        thisFormTxt.close()

      
        # Create a thread to send the emails, allowing the page to render while this is going  on
        #   so the customer doesn't have to wait
        t1 = Thread(target=send_emails,
                    args=(f'{cust_fName} {cust_lName}',
                          request.form.get('Email'),
                          request.form.get('Phone Number'), order_date,
                          f'./forms/{pathExt}', cust_total))
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
