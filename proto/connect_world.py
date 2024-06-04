# -*- coding: utf-8 -*-
import socket
import world_amazon_pb2
import amazon_ups_pb2 
from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _VarintEncoder
import psycopg2
import concurrent.futures
import threading
import time
import os
import os.path
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import socket
import time

db_lock = threading.Lock()
seqnum = 1

#Create a socket
def create_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Socket created")  
    return s


def send_confirmation_email(cursor, order_id):
    status_query = """
    SELECT status
    FROM order_order
    WHERE order_order.id = %s
    """
    cursor.execute(status_query, (order_id,))
    # print("cursor executed")
    status_result = cursor.fetchone()
    status = status_result[0]
    # Use Gmail API for sending emails
    service = gmail_authenticate()

    buyer_query = """
    SELECT buyer_id
    FROM order_order
    WHERE order_order.id = %s
    """

    cursor.execute(buyer_query, (order_id,))
    buyer_id_result = cursor.fetchone()
    buyer_id = buyer_id_result[0]
    


    email_query = """
    SELECT email
    FROM account_userprofile
    WHERE account_userprofile.user_id = %s
    """

    cursor.execute(email_query, (buyer_id,))
    owner_email_result = cursor.fetchone()
    owner_email = owner_email_result[0]

    # Email content
    sender_email = "m271693043@gmail.com"

    subject = "Order Update From Amazon"

    message_body = f"Dear {owner_email},\n\nYour order from Amazon, order id {order_id}, has been updated to {status}.\n\n"

    message_body += "Thank you for choosing Amazon."

    # Send emails
    send_message_gmail(service, sender_email, owner_email, subject, message_body)

#Connet to a server
def connect_to_server(sock, port, host):
    if not host:
        host = 'vcm-38382.vm.duke.edu'
    host_ip = socket.gethostbyname(host)
    sock.connect((host_ip, port))
    print("Connected to the server")

#Send a message to the world
def send_message(sock, message):
    encode_message = message.SerializeToString()
    size = []
    _VarintEncoder()(size.append, len(encode_message), False)
    size_b = b''.join(size)
    sock.sendall(size_b+encode_message)
    print("Send message: ", message)

#Receive a message from the world
def receive_message(sock):
    var_int_buff = []
    while True:
        try:
            buf = sock.recv(1)
            var_int_buff += buf
            msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
            if new_pos != 0:
                break
        except IndexError:
            pass
    whole_message = sock.recv(msg_len)
    return whole_message

def UprintMessage(ack_message):
    ack_message_decode = amazon_ups_pb2.UACommands()
    ack_message_decode.ParseFromString(ack_message)
    print("***Response (UPS):")
    print(ack_message_decode)
    return ack_message_decode

def WprintMessage(ack_message):
    ack_message_decode = world_amazon_pb2.AResponses()
    ack_message_decode.ParseFromString(ack_message)
    print("***Response (World):")
    print(ack_message_decode)
    return ack_message_decode
    

#Pack a list of products, return a APack msg
def packProducts(products_list, whnum, shipid, seqnum):
    pack_msg = world_amazon_pb2.APack()
    pack_msg.whnum = whnum
    pack_msg.shipid = shipid
    pack_msg.seqnum = seqnum
    for product in products_list:
        pack_msg.things.append(product)
    return pack_msg

#generate a purchaseMore msg
def purchaseProducts(products_list, whnum, seqnum):
    purchase_msg = world_amazon_pb2.APurchaseMore()
    purchase_msg.whnum = whnum
    purchase_msg.seqnum = seqnum
    for product in products_list:
        purchase_msg.things.append(product)
    return purchase_msg

#Return a APutOnTruck msg
def loadPack(whnum, truckid, shipid, seqnum):
    load_msg = world_amazon_pb2.APutOnTruck()
    load_msg.whnum = whnum
    load_msg.truckid = truckid
    load_msg.shipid = shipid
    load_msg.seqnum = seqnum
    return load_msg

#Listen to the frontend
def listenToClient(sock, port, host):
    if not host:
        # host = '152.3.77.215'
        host = '67.159.95.216'
    sock.bind((host, port))
    sock.listen()  
    print("Server created, waiting for connection")

#Connect to the same db
def connectToDB():
    conn = psycopg2.connect(
        dbname = "miniamazon",
        user = "ericmu",
        password = "miniamazon",
        host = "localhost",
        port = "5432"
    )
    cursor = conn.cursor()
    return cursor, conn

def get_product_details(cursor, order_id):
    try:
        # print("enter details")
        query = """
        SELECT product_id, description, order_order.quantity, buyer_id, ups_account_name, truck_id
        FROM order_order
        JOIN order_product ON order_order.product_id = order_product.id
        WHERE order_order.id = %s
        """
        cursor.execute(query, (order_id,))
        # print("cursor executed")
        result = cursor.fetchone()
        # print("table fetched")
        product_id, description, quantity, buyer_id, ups_account_name, truck_id = result
        # print("table got results")
        return product_id, description, quantity, buyer_id, ups_account_name, truck_id
    except (Exception, psycopg2.Error) as e:
        print(f"Error in details: {e}")

def buyProducts(sock, whnum, seqnum):
    #Purchase products to warehouse
    product1 = world_amazon_pb2.AProduct()
    product1.id = 1
    product1.description = "Product 1"
    product1.count = 9999

    product2 = world_amazon_pb2.AProduct()
    product2.id = 2
    product2.description = "Product 2"
    product2.count = 9999

    product3 = world_amazon_pb2.AProduct()
    product3.id = 3
    product3.description = "Product 3"
    product3.count = 9999

    product4 = world_amazon_pb2.AProduct()
    product4.id = 4
    product4.description = "Product 4"
    product4.count = 9999

    product5 = world_amazon_pb2.AProduct()
    product5.id = 5
    product5.description = "Product 5"
    product5.count = 9999

    product6 = world_amazon_pb2.AProduct()
    product6.id = 6
    product6.description = "Product 6"
    product6.count = 9999

    product7 = world_amazon_pb2.AProduct()
    product7.id = 7
    product7.description = "Product 7"
    product7.count = 9999

    product8 = world_amazon_pb2.AProduct()
    product8.id = 8
    product8.description = "Product 8"
    product8.count = 9999

    product9 = world_amazon_pb2.AProduct()
    product9.id = 9
    product9.description = "Product 9"
    product9.count = 9999

    product10 = world_amazon_pb2.AProduct()
    product10.id = 10
    product10.description = "Product 10"
    product10.count = 9999

    product11 = world_amazon_pb2.AProduct()
    product11.id = 11
    product11.description = "Product 11"
    product11.count = 9999

    product12 = world_amazon_pb2.AProduct()
    product12.id = 12
    product12.description = "Product 12"
    product12.count = 9999

    product_list = [product1, product2,product3,product4,product5,product6,product7,product8,product9,product10,product11,product12]
    # product_list = [product1, product2,product3]
    purchase_msg = purchaseProducts(product_list, whnum, seqnum)

    command = world_amazon_pb2.ACommands()
    command.buy.append(purchase_msg)
    send_message(sock, command)
    # ack_message2 = receive_message(sock)
    # WprintMessage(ack_message2)

def connect_world(sock_world, sock_ups):
    #Connect to the same world as UPS
    message_encode = receive_message(sock_ups)
    message = amazon_ups_pb2.UAInitConnect()
    message.ParseFromString(message_encode)

    build_connect = world_amazon_pb2.AConnect()
    build_connect.worldid = message.worldid
    initWareHouse = world_amazon_pb2.AInitWarehouse()
    initWareHouse = build_connect.initwh.add()
    initWareHouse.id = 1
    initWareHouse.x = 1
    initWareHouse.y = 1
    build_connect.isAmazon = True
    send_message(sock_world, build_connect)
    ack_message = receive_message(sock_world)
    ack_message_decode = world_amazon_pb2.AConnected()
    ack_message_decode.ParseFromString(ack_message)
    print("***Response (Connect World):")
    print(ack_message_decode)

    #After connected, send ack to ups
    init_ack = amazon_ups_pb2.AUConfirmConnect()
    init_ack.worldid = message.worldid
    init_ack.connected = 1
    send_message(sock_ups, init_ack)

    return message

def update_order_status(cursor, conn, order_id, new_status):
    order_id = int(order_id)
    update_query = "UPDATE order_order SET status = %s WHERE id = %s;"
    cursor.execute(update_query, (new_status, int(order_id)))
    conn.commit()
    send_confirmation_email(cursor, order_id)
    if cursor.rowcount:
        print(f"Order {order_id} updated to status '{new_status}'.")
    else:
        print(f"No order found with ID {order_id}, or the status is already '{new_status}'.")

def listenFrontendMessage(cursor, sock_frontend, sock_world, whnum, conn):
    while (True):
        client_sock2, addr = sock_frontend.accept()
        print("Get connection from frontend")
        id = client_sock2.recv(1024)
        if id:
            print("Get id: ", id.decode())
            thread = threading.Thread(target=processFrontendMessage, args=(cursor, sock_frontend, sock_world, whnum, id,conn,))
            thread.start()

def processFrontendMessage(cursor, sock_frontend, sock_world, whnum, id, conn):
    # while (True):
    #     client_sock2, addr = sock_frontend.accept()
    #     print("Get connection from {addr}")
    #     id = client_sock2.recv(1024)
    #     if not id:
    #         break
    #     if id:
    #         print("Get id: ", id.decode())

            #Get order detail
            product_id, description, quantity, buyer_id, ups_account_name, truck_id = get_product_details(cursor, int(id))
            print("got details")
            product1 = world_amazon_pb2.AProduct()
            product1.id = product_id
            product1.description = description
            product1.count = quantity

            print("prepare pack msg")
            pack_msg = world_amazon_pb2.APack()
            print("before pack")
            global seqnum
            try:
                pack_msg = packProducts([product1], whnum, int(id), seqnum)
            except (Exception) as e:
                print(f"Error in details: {e}")
            print("after pack")
            seqnum += 1

            print("pack command")
            #pack order
            command = world_amazon_pb2.ACommands()
            command.topack.append(pack_msg)
            print("ready to send")
            send_message(sock_world, command)
            db_lock.acquire()
            try:
                update_order_status(cursor, conn, id, "packing")
            except (Exception, psycopg2.Error) as e:
                print(f"Error in details: {e}")
            finally:
                db_lock.release()

def listenWorldMessage(sock_world, client_sock, cursor, conn):
    while (True):
        message = receive_message(sock_world)
        if message:
            thread = threading.Thread(target=processWorldMessage, args=(sock_world, client_sock, cursor, conn, message,))
            thread.start()

def processWorldMessage(sock_world, client_sock, cursor, conn, message):
    # while (True):
    #     message = receive_message(sock_world)
    #     if not message:
    #         break
    #     if message:
            global seqnum
            print("enter world messsage")
            message_decode = WprintMessage(message)
            # if message_decode.ready or message_decode.loaded or message_decode.arrived or message_decode.finished:
            #     print("enter return messasge")
            #     command9 = world_amazon_pb2.ACommands()
            #     for ack in message_decode.acks:
            #         command9.acks.append(ack)
            #     send_message(sock_world, command9)

            if message_decode.arrived:
                command9 = world_amazon_pb2.ACommands()
                for item in message_decode.arrived:
                    command9.acks.append(item.seqnum)
                send_message(sock_world, command9)

            if message_decode.finished:
                command9 = world_amazon_pb2.ACommands()
                for item in message_decode.finished:
                    command9.acks.append(item.seqnum)
                send_message(sock_world, command9)

            if message_decode.ready:
                command9 = world_amazon_pb2.ACommands()
                for item in message_decode.ready:
                    command9.acks.append(item.seqnum)
                send_message(sock_world, command9)
                for item in message_decode.ready:
                    #pack is packed, send message to ups to order a truck
                    id = item.shipid
                    db_lock.acquire()
                    try:
                        update_order_status(cursor, conn, id, "packed")
                    except (Exception, psycopg2.Error) as e:
                        print(f"Error in details: {e}")
                    finally:
                        db_lock.release()

                    product_id, description, quantity, buyer_id, ups_account_name, truck_id = get_product_details(cursor, int(id))
                    product2 = amazon_ups_pb2.Product()
                    product2.id = product_id
                    product2.description = description
                    product2.count = quantity

                    pack_msg2 = amazon_ups_pb2.Pack()
                    pack_msg2.wh_id = 1
                    pack_msg2.things.append(product2)
                    pack_msg2.trackingid = str(id)
                    pack_msg2.dest_x = 1
                    pack_msg2.dest_y = 1
                    pack_msg2.amazonaccount = buyer_id
                    pack_msg2.packageid = id
                    if ups_account_name:
                        pack_msg2.upsaccount = int(ups_account_name)
                    
                    needTruck_msg = amazon_ups_pb2.AUNeedATruck()
                    needTruck_msg.pack.CopyFrom(pack_msg2)
                    needTruck_msg.seqnum = seqnum
                    seqnum += 1

                    command2 = amazon_ups_pb2.AUCommands()
                    command2.need.append(needTruck_msg)
                    send_message(client_sock, command2)
        
            if message_decode.loaded:
                command9 = world_amazon_pb2.ACommands()
                for item in message_decode.loaded:
                    command9.acks.append(item.seqnum)
                send_message(sock_world, command9)
                
                for item in message_decode.loaded:
                    #Package is loaded, send a message to ups, let truck go
                    id = item.shipid
                    
                    db_lock.acquire()
                    try:
                        update_order_status(cursor, conn, id, "loaded")
                    except (Exception, psycopg2.Error) as e:
                        print(f"Error in details: {e}")
                    finally:
                        db_lock.release()

                    product_id, description, quantity, buyer_id, ups_account_name, truck_id = get_product_details(cursor, int(id))
                    canGo_msg = amazon_ups_pb2.AUTruckCanGo()
                    canGo_msg.truckid = truck_id
                    canGo_msg.seqnum = seqnum
                    seqnum += 1
                    command4 = amazon_ups_pb2.AUCommands()
                    command4.go.append(canGo_msg)
                    send_message(client_sock, command4)

                    db_lock.acquire()
                    try:
                        update_order_status(cursor, conn, id, "On the way")
                    except (Exception, psycopg2.Error) as e:
                        print(f"Error in details: {e}")
                    finally:
                        db_lock.release()
                    # Send email updates to the user
                    # send_confirmation_email(id)



# Authentication and service creation
# Code adapted from ED instructor sample code
def gmail_authenticate():
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    creds = None
    # token.json stored user access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # Authentication if no valid credentials are available
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This credentials.json is the credential you download from Google API portal when you 
            # created the OAuth 2.0 Client IDs
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            # this is the redirect URI which should match your API setting, you can 
            # find this setting in Credentials/Authorized redirect URIs at the API setting portal
            creds = flow.run_local_server(host='127.0.0.1', port=8080, open_browser = False)

        # Save vouchers for later use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

# Code adapted from ED instructor sample code
def send_message_gmail(service, sender, to, subject, msg_html):
    message = MIMEMultipart('alternative')
    message['from'] = sender
    message['to'] = to
    message['subject'] = subject

    msg = MIMEText(msg_html, 'html')
    message.attach(msg)

    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    body = {'raw': raw}

    message = (service.users().messages().send(userId="me", body=body).execute())
    print(f"Message Id: {message['id']}")



def listenUPSMessage(sock_world, cursor, conn, client_sock):
    while (True):
        message = receive_message(client_sock)
        if message:
            thread = threading.Thread(target=processUPSMessage, args=(sock_world, cursor, conn, client_sock, message, ))
            thread.start()


def processUPSMessage(sock_world, cursor, conn, client_sock, message):
    # while (True):
    #     message = receive_message(sock_world)
    #     if not message:
    #         break
    #     if message:
            global seqnum
            message_decode = UprintMessage(message)
            if message_decode.arrived:
                command9 = amazon_ups_pb2.AUCommands()
                
                for item in message_decode.arrived:
                    command9.acks.append(item.seqnum)
                send_message(client_sock, command9)

                for item in message_decode.arrived:
                    #Truck arrived, send message to world to load packages
                    truck_id = item.truckid
                    id = item.trackingid

                    update_query = "UPDATE order_order SET truck_id = %s WHERE id = %s;"
                    db_lock.acquire()
                    try:
                        cursor.execute(update_query, (truck_id, int(id)))
                        conn.commit()
                    except (Exception, psycopg2.Error) as e:
                        print(f"Error in details: {e}")
                    finally:
                        print("to release")
                        db_lock.release()
                        print("released")

                    whnum = item.wh_id
                    load_msg = world_amazon_pb2.APutOnTruck()
                    load_msg.whnum = whnum
                    load_msg.truckid = truck_id
                    load_msg.shipid = int(id)
                    load_msg.seqnum = seqnum
                    seqnum += 1
                    command3 = world_amazon_pb2.ACommands()
                    command3.load.append(load_msg)
                    send_message(sock_world, command3)
                    db_lock.acquire()
                    try:
                        update_order_status(cursor, conn, id, "Loading")
                    except (Exception, psycopg2.Error) as e:
                        print(f"Error in details: {e}")
                    finally:
                        db_lock.release()


            if message_decode.delivered:
                command9 = amazon_ups_pb2.AUCommands()
                
                for item in message_decode.delivered:
                    command9.acks.append(item.seqnum)
                send_message(client_sock, command9)

                for item in message_decode.delivered:
                    id = item.trackingid
                    
                    db_lock.acquire()
                    try:
                        update_order_status(cursor, conn, id, "Delivered")
                    except (Exception, psycopg2.Error) as e:
                        print(f"Error in details: {e}")
                    finally:
                        db_lock.release()
                    # Send email updates to the user
                    # send_confirmation_email(id)

            if message_decode.changeAddr:
                command9 = amazon_ups_pb2.AUCommands()
                
                for item in message_decode.changeAddr:
                    command9.acks.append(item.seqnum)
                send_message(client_sock, command9)

                for item in message_decode.changeAddr:
                    id = item.trackingid
                    x = item.dest_x
                    y = item.dest_y
                    update_query = "UPDATE order_order SET address_x = %s, address_y = %s WHERE id = %s;"
                    
                    db_lock.acquire()
                    try:
                        cursor.execute(update_query, (x, y, int(id)))
                        conn.commit()
                    except (Exception, psycopg2.Error) as e:
                        print(f"Error in details: {e}")
                    finally:
                        db_lock.release()


def runAmazon():
    cursor, conn = connectToDB()
    #Connect to the world server
    port1 = 23456
    sock_world = create_socket()
    if sock_world is not None:
        connect_to_server(sock_world, port1, "152.3.53.96")
        # connect_to_server(sock_world, port1, "vcm-38161.vm.duke.edu")
    #Connect to UPS, change port and host name
    port2 = 9999
    sock_ups = create_socket()
    if sock_ups is not None:
        listenToClient(sock_ups, port2, None)
        client_sock, addr = sock_ups.accept()
        print("Get connection from {addr}")
    #Listen to the frontend
    sock_frontend = create_socket()
    if sock_frontend is not None:
        listenToClient(sock_frontend, 45678, None)
    #connect to the same world, get world id from ups
    message = connect_world(sock_world, client_sock)
    command = world_amazon_pb2.ACommands()
    command.simspeed = 500
    send_message(sock_world, command)
    #Buy product to warehouse
 
    global seqnum
    buyProducts(sock_world, 1, seqnum)

    seqnum += 1


    #major part of Amazon
    # with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    #     # while (True):
    #         future1 = executor.submit(processFrontendMessage, cursor, sock_frontend, sock_world, seqnum, 1)
    #         future2 = executor.submit(processWorldMessage, sock_world, client_sock, cursor, conn, seqnum)
    #         future3 = executor.submit(processUPSMessage, sock_world, cursor, conn, seqnum, client_sock)
            # time.sleep(1)

    thread1 = threading.Thread(target=listenFrontendMessage, args=(cursor, sock_frontend, sock_world, 1,conn, ))
    thread2 = threading.Thread(target=listenWorldMessage, args=(sock_world, client_sock, cursor, conn,))
    thread3 = threading.Thread(target=listenUPSMessage, args=(sock_world, cursor, conn, client_sock, ))

    thread1.start()
    thread2.start()
    thread3.start()

def main():
    runAmazon()
    # cursor, conn = connectToDB()

    # #Connect to the world server
    # port1 = 23456
    # sock_world = create_socket()
    # if sock_world is not None:
    #     connect_to_server(sock_world, port1, "vcm-38153.vm.duke.edu")

    # #Connect to UPS, change port and host name
    # port2 = 9999
    # sock_ups = create_socket()
    # if sock_ups is not None:
    #     listenToClient(sock_ups, port2, None)
    #     client_sock, addr = sock_ups.accept()
    #     print("Get connection from {addr}")

    # #Listen to the frontend
    # sock_frontend = create_socket()
    # if sock_frontend is not None:
    #     listenToClient(sock_frontend, 45678)

    # #connect to the same world, get world id from ups
    # message = connect_world(sock_world, client_sock)

    # seqnum = 1

    # #Buy product to warehouse
    # buyProducts(sock_world, message.worldid, seqnum)
    # seqnum += 1

    # while True:
    #     #Get order id from the frontend
    #     client_sock2, addr = sock_frontend.accept()
    #     print("Get connection from {addr}")
    #     id = client_sock2.recv(1024)
    #     if not id:
    #         break
    #     print("Get id: ", id.decode())
        
    #     #Get order detail
    #     product_id, description, quantity, buyer_id, ups_account_name, truck_id = get_product_details(cursor, id)
    #     product1 = world_amazon_pb2.AProduct()
    #     product1.id = product_id
    #     product1.description = description
    #     product1.count = quantity

    #     pack_msg = world_amazon_pb2.APack()
    #     pack_msg = packProducts([product1], message.worldid, id, seqnum)
    #     seqnum += 1

    #     #pack order
    #     command = world_amazon_pb2.ACommands()
    #     command.topack.append(pack_msg)
    #     send_message(sock_world, command)
    #     ack_message2 = receive_message(sock_world)
    #     WprintMessage(ack_message2)
        
    #     #Need a truck from ups
    #     product2 = amazon_ups_pb2.Product()
    #     product2.id = product_id
    #     product2.description = description
    #     product2.count = quantity

    #     pack_msg2 = amazon_ups_pb2.Pack()
    #     pack_msg2.wh_id = message.worldid
    #     pack_msg2.things.append(product2)
    #     pack_msg2.trackingid = id
    #     pack_msg2.dest_x = 1
    #     pack_msg2.dest_y = 1
    #     pack_msg2.amazonaccount = buyer_id
    #     if ups_account_name:
    #         pack_msg2.upsaccount = ups_account_name
        
        
    #     needTruck_msg = amazon_ups_pb2.AUNeedATruck()
    #     needTruck_msg.pack.append(pack_msg2)
    #     needTruck_msg.seqnum = seqnum
    #     seqnum += 1

    #     command2 = amazon_ups_pb2.AUCommands()
    #     command2.need.append(needTruck_msg)
    #     command2.acks.append(seqnum-1)
    #     seqnum += 1

    #     send_message(client_sock, command2)
    #     ack_message3 = receive_message(sock_world)
    #     ack_message_decode3 = amazon_ups_pb2.UATruckArrived()
    #     ack_message_decode3.ParseFromString(ack_message3)
    #     print("***Response (Need a truck):")
    #     print(ack_message_decode3)
    #     truck_id = ack_message_decode3.arrived.truckid
        
    #     #load
    #     load_msg = world_amazon_pb2.APutOnTruck()
    #     load_msg.whnum = message.worldid
    #     load_msg.truckid = truck_id
    #     load_msg.shipid = id
    #     load_msg.seqnum = seqnum
    #     seqnum += 1

    
if __name__ == '__main__':
    main()
