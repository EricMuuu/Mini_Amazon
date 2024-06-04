from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint
import world_ups_pb2
import amazon_ups_pb2
import psycopg2
from psycopg2 import pool
import threading

class ThreadSafeSequenceNumber:
    def __init__(self, start=0):
        self.current = start
        self.lock = threading.Lock()
        self.ack_received = {}
        self.ack_events = {}

    def next(self):
        with self.lock:
            self.current += 1
            self.ack_received[self.current] = False
            self.ack_events[self.current] = threading.Event()
            return self.current

    def acknowledge(self, seq_num):
        with self.lock:
            if seq_num in self.ack_received:
                self.ack_received[seq_num] = True
                self.ack_events[seq_num].set()
                return True
            return False

# Usage in a multi-threaded environment
seq_world = ThreadSafeSequenceNumber()
seq_amazon = ThreadSafeSequenceNumber()

def create_dbconnection_pool():
    try:
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,              
            maxconn=10,            
            host='localhost',     
            user='postgres',  
            password='postgres',
            database='ups' 
        )

        if connection_pool:
            print("Connection pool created successfully")
            return connection_pool
        else:
            print("Connection pool created failed")
    except (Exception, psycopg2.DatabaseError) as e:
        print("Error while creating connection pool", e)

def init_UConnect(db_pool):
    connect_message = world_ups_pb2.UConnect()
    # connect_message.worldid = 1
    connect_message.isAmazon = False

    for i in range(1, 100):
        truck = init_truck(i, db_pool)
        connect_message.trucks.extend([truck])
        # TO DO: add truck to idle_trucks

    return connect_message

def init_truck(truckid, db_pool):
    truck = world_ups_pb2.UInitTruck()
    truck.id = truckid
    truck.x = 100
    truck.y = 100

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            init_truck_stmt = """
            INSERT INTO delivery_truck (truckId, status, x, y)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(init_truck_stmt, (truckid, 0, truck.x, truck.y))
            conn.commit() 
    except Exception as e:
        conn.rollback()
        print(f"Failed to initialize truck in database: {e}")
    finally:
        db_pool.putconn(conn)
    return truck

def init_UAConnect(id):
    connect_message = amazon_ups_pb2.UAInitConnect()
    connect_message.worldid = id

    return connect_message

def send_protobuf(socket, message):
    # Serialize the message to bytes
    data = message.SerializeToString()
    # Send the size of the message as a varint
    _EncodeVarint(socket.send, len(data), None)
    # Send the actual message
    socket.sendall(data)

def init_database(db_pool):
    conn = db_pool.getconn()
    with conn.cursor() as cursor:
        init_stmt = """
            DROP TABLE IF EXISTS delivery_user;
            DROP TABLE IF EXISTS delivery_truck;
            DROP TABLE IF EXISTS delivery_order;

            CREATE TABLE delivery_order (
                trackingid VARCHAR(50) NOT NULL,
                packageid INTEGER NOT NULL,
                orderid SERIAL PRIMARY KEY,
                status INTEGER NOT NULL,
                warehouseid INTEGER NOT NULL,
                destx INTEGER NOT NULL,
                desty INTEGER NOT NULL,
                uidamazon INTEGER NOT NULL,
                processtime TIMESTAMP WITH TIME ZONE,
                loadtime TIMESTAMP WITH TIME ZONE,
                deliverytime TIMESTAMP WITH TIME ZONE,
                completetime TIMESTAMP WITH TIME ZONE,
                truck_id INTEGER NOT NULL
            );

            CREATE TABLE delivery_truck (
                truckid SERIAL PRIMARY KEY,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                status INTEGER NOT NULL
            );

            CREATE TABLE delivery_user (
                uid SERIAL PRIMARY KEY,
                password CHARACTER VARYING(128) NOT NULL,
                last_login TIMESTAMP WITH TIME ZONE,
                is_superuser BOOLEAN NOT NULL,
                first_name CHARACTER VARYING(150) NOT NULL,
                last_name CHARACTER VARYING(150) NOT NULL,
                email CHARACTER VARYING(254) NOT NULL,
                is_staff BOOLEAN NOT NULL,
                is_active BOOLEAN NOT NULL,
                date_joined TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """
        cursor.execute(init_stmt)
        conn.commit()
    db_pool.putconn(conn)
    pass

# def handle_uwresponse(response, dbconnection_pool):
#     if response.acks:
#         # compare ack with seq_num
#         pass
#     if response.completions:
#         # update database: truck status
#         # send message to amazon
#         pass
#     if response.delivered:
#         # update database: package status
#         # send message to amazon
#         pass
#     if response.finished:
#         # 
#         pass
#     if response.truckstatus:
#         # update database: truct status
#         pass
#     if response.error:
#         print(f"Error Info From World: {response.error}")
#         pass

# def handle_uaresponse(response, dbconnection_pool, amazon_socket, world_socket):
#     if response.need:
#         for need in response.need:
#             connection = dbconnection_pool.getconn()
#             try:
#                 with connection.cursor() as cursor:
#                     for order in need.orders:
#                         cursor.execute(
#                             """INSERT INTO package (x, y, status, packageid, amzaccount, upsaccount) 
#                             VALUES (%s, %s, %s, %s, %s, %s) 
#                             ON CONFILICT (packageid) DO UPDATE
#                             SET x = EXCLUDED.x, y = EXCLUDED.y;""",
#                             (order.x, order.y, "traveling", order.trackingid, order.amzaccount, order.upsaccount)
#                         )
#                         connection.commit()
#             finally:
#                 dbconnection_pool.putconn(connection)
#             truck_id = allocate_truck()
#             if truck_id is not None:
#                 send_amazon_ack(amazon_socket, response.ack)
#             else:
#                 print('No idle truck')
#             # send pick up request to world
#             send_go_pick_world(world_socket, truck_id)
#             # recv ack from world

#     if response.go:
#         # update truck status
#         # send go to world
#         # update order status
#         # send ack to amazon
#         for go in response.go:
#             connection = dbconnection_pool.getconn()
#             try:
#                 with connection.cursor() as cursor:
#                     cursor.execute(
#                         "UPDATE truck SET status=%s WHERE truckid=%s;",
#                         ('traveling', go.truckid)
#                     )
#                     packages = world_ups_pb2.UDeliveryLocation()
#                     for order in go.orders:
#                         cursor.execute(
#                             "UPDATE package SET status=%s WHERE packageid=%s;",
#                             ('traveling', order.trackingid)
#                         )
#                         package = world_ups_pb2.UDeliveryLocation()
#                         # packageid and trackingid
#                         package.packageid = order.trackingid
#                     connection.commit()
#                     package = world_ups_pb2.UDeliveryLocation()
                    
#                     send_deliver_to_world(world_socket, go.truckid, packages)
#                     send_amazon_ack(amazon_socket, go.seqnum)
#                     # recv ack from world

#             except Exception as e:
#                 connection.rollback()
#                 print(f"Error processing go message: {e}")
#             finally:
#                 dbconnection_pool.putconn(connection)
#     if response.error:
#         print(f"Error Info From Amazon: {response.error}")
#         pass
#     if response.acks:
#         pass


# def allocate_truck():

#     return

# def send_deliver_to_world(socket, truckid, package):
#     message = world_ups_pb2.UCommands()
#     deliver_msg = world_ups_pb2.UGoDeliver()
#     deliver_msg.truckid = truckid
#     deliver_msg.package = package
#     deliver_msg.seqnum = 1
#     message.deliveries = deliver_msg
#     message.seqnum = 1
#     send_protobuf(socket, message)
#     return

# def send_go_pick_world(socket, truckid):
    pass