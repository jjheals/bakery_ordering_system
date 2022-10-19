
from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask import render_template, request
from gevent.pywsgi import WSGIServer
from flask_compress import Compress
from os import mkdir, listdir
from werkzeug.utils import secure_filename

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

def send_emails(customer_name, customer_email, order_date, folderPath):
    # General constants
    port = 0 # Redacted
    password = '' # Redacted
    smtp_server = '' # Redacted
    sender_email = "" # Redacted

    # ---------- + ---------- #
    # Confirmation message to the customer
    
    conf_message = EmailMessage()
    conf_message['Subject'] = 'Order Inquiry Confirmation'
    conf_message['From'] = "Josie's Bakery"
    conf_message['To'] = customer_email
    conf_message.set_content(f"Hello {customer_name},\n\nWe have received your email for {order_date}. Please allow us up to two days to process your order, we will be in touch soon!\n\nBest,\nThe Josie's Bakery Team")
   
    # ---------- + ---------- #
    # Notification message to the bakery
    bakery_email = '' # Redacted

    notif_msg = EmailMessage()
    notif_msg["From"] = customer_email
    notif_msg["Subject"] = f"New Order Inquiry from {customer_name}"
    notif_msg["To"] = bakery_email
    notif_msg.set_content(f"{customer_name} has submitted a new order for {order_date}.\n\nOrder details attached.")
    notif_msg.add_attachment(open(f'{folderPath}/order-details.txt', "r").read(), filename="order-details.txt")

    with smtplib.SMTP_SSL(smtp_server, port) as smtp:
        smtp.login(sender_email, password)
        smtp.send_message(notif_msg)
        print('Notification message sent.')
        smtp.send_message(conf_message)
        print('Confirmation message sent.')
        smtp.close()

    
#------------------------------------------------------------------------------------#
# Function to iterate through the orders based on criteria
# Returns a list of Orders (object)
def searchAllOrders(date, name):
    
    loo = listdir('./forms/') # List of all order folders
    loio = [] # List of all INVALID orders to be removed
    names = str(name).split() # Get the first and last name from the input field as separate strings
    
    i=0
    while i <= len(loo)-1:
        order=loo[i]
        
        # Check the name (first and last but separately)
        # NOTE: Print statements are for debugging & error checking purposes
        for n in names:
            if not order in loio:         
                if n in order:
                    print(f'\nFOUND VALID ORDER {order}')
                else: 
                    print(f'\nFOUND INVALID ORDER (name). ADDING: {order} to "loio"')
                    loio.append(order)
        
        # Check if the date is incorrect, and check if order is not already in loio, add if both true
        if (not date in order) and (not order in loio): 
            print(f'FOUND INVALID ORDER (date). ADDING {order} to "loio"')
            loio.append(order)
        
        i+=1
                    
    # Remove all the invalid orders from loo
    for order in loio: 
        loo.remove(order)
    
    return loo 


#------------------------------------------------------------------------------------#
# Code for handling server requests

app = Flask(__name__)

compress = Compress()
compress.init_app(app)


# ---------- + ---------- #
# Rendering the home page with the form
@app.route('/')
def index():
    return render_template('index.html')


# ---------- + ---------- #
# Rendering the post-submission page
@app.route('/received', methods=['POST'])
def submission():
    loi = request.files.getlist('Images')
    cust_fName = request.form.get('First Name')
    cust_lName = request.form.get('Last Name')
    order_date = request.form.get('Date')
    pathExt = f'/{cust_fName}-{cust_lName}_{order_date}'
    
    mkdir(f'./forms/{pathExt}') # Make a directory to store the order details and reference images in one place
    thisFormTxt = open(f'./forms/{pathExt}/order-details.txt', 'w+') # Create a text file with the order details 
    loe = request.form
    seen = []
    
    # Write to the text file with the relevant order details
    # NOTE: Is there a better way to do this??? Maybe to improve efficiency???
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
            
    # Save the reference images, if applicable
    thisFormTxt.write(f'\nNumber of files: {len(loi)}')
    print(f'Saving {len(loi)} images . . . ')
    for i in loi:
        i.save(f'./forms/{pathExt}/{secure_filename(i.filename)}')

    # Create a thread to send the emails, allowing the page to render while this is going on
    #   so the customer doesn't have to wait 
    t1 = Thread(target=send_emails, args=(f'{cust_fName} {cust_lName}', request.form.get('Email'), order_date, f'./forms{pathExt}'))
    t1.start()
    
    print('Rendering template')
    return render_template('submission-received.html')
    

# ---------- + ---------- #
# To access employee login page

# Not complete!!!
# -> Need to add authentication & security
# -> Need to put the button in a better place on the form page
@app.route('/employee-login', methods=['POST'])
def login():
    return render_template('login.html')



# ---------- + ---------- #
if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 0), app) # Port redacted
    http_server.serve_forever()
