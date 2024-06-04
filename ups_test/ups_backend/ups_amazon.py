from datetime import datetime
import psycopg2
import random
# from ups_world import send_GoPickup, send_GoDeliver
import amazon_ups_pb2
import world_ups_pb2
from utils import seq_amazon, seq_world, send_protobuf

# amazon
def process_uaresponse(message, db_pool, world_socket, amazon_socket):
    if message.need:
        for truck in message.need:
            # print(f"In uaresponse :\n {truck}")
            # print("truck.seq_num : ", truck.seqnum)
            send_amazon_ack(amazon_socket, truck.seqnum)
            process_need(truck, db_pool, world_socket)

    if message.go:
        for truck in message.go:
            send_amazon_ack(amazon_socket, truck.seqnum)
            process_go(truck, db_pool, world_socket)

    if message.errors:
        for err in message.errors:
            send_amazon_ack(amazon_socket, err.seqnum)
            print(f"Error: {err.err} in response to message {err.originseqnum}")

    if message.acks:
        # TO DO: handle acks
        for ack in message.acks:
            seq_amazon.acknowledge(ack)
            print(f"Acknowlegment for amazon ack {ack}")

def process_need(truck, db_pool, world_socket):
    # print(-1)
    pack = truck.pack
    wh_id = pack.wh_id
    package_id = pack.packageid
    # print(0)
    trackingid = pack.trackingid
    upsaccount = pack.upsaccount if pack.HasField('upsaccount') else None
    amazonaccount = pack.amazonaccount
    # print(0.5)
    dest_x = pack.dest_x
    dest_y = pack.dest_y
    # print(1)
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            insert_order_stmt = """
            INSERT INTO delivery_order (warehouseid, uidAmazon, status, trackingid, packageid, destX, destY, truck_id, processtime)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING trackingid;
            """
            # TO DO: assign truck_id seq_num
            # print(2)
            truck_id = select_truck(db_pool)
            seq_num = seq_world.next()
            cursor.execute(insert_order_stmt, (wh_id, amazonaccount, 0, trackingid, package_id, dest_x, dest_y, truck_id, datetime.now()))
            order_id = cursor.fetchone()[0]
            
            conn.commit()
            # print(f"Order {order_id} has been inserted into the database.")
            
            # TO DO: send UGoPickup to world
            # print("Sending GoPickup to World!")
            send_GoPickup(wh_id, truck_id, seq_num, world_socket, db_pool)
            # print("GoPickup Sent to world!")

    except (Exception, psycopg2.Error) as e:
        print(f"Database error during inserting order: {e}")
        conn.rollback()
    finally:
        db_pool.putconn(conn)

def process_go(truck, db_pool, world_socket):
    truck_id = truck.truckid

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            update_truck_stmt = """
            UPDATE delivery_truck
            SET status = %s
            WHERE truckid = %s;
            """
            cursor.execute(update_truck_stmt, (3, truck_id))
            conn.commit()
            # print(f"Truck {truck_id} status has been updated to 3 in the database.")
            seq_num = seq_world.next()
            # TO DO: send UGoDeliver to world
            send_GoDeliver(truck_id, seq_num, world_socket, db_pool)

    except (Exception, psycopg2.Error) as e:
        print(f"Database error during updating truck status: {e}")
        conn.rollback()
    finally:
        db_pool.putconn(conn)

def send_UATruckArrived(truck_id, tracking_id, wh_id, seq_num, amazon_socket):
    print(f"Sending truck arrived, seq_num: {seq_num}")
    truck_arrived = amazon_ups_pb2.UATruckArrived()
    truck_arrived.truckid = truck_id
    truck_arrived.trackingid = tracking_id
    truck_arrived.wh_id = wh_id
    truck_arrived.seqnum = seq_num

    ua_commands = amazon_ups_pb2.UACommands()
    ua_commands.arrived.append(truck_arrived)
    # TO DO: accept acks
    ack_event = seq_amazon.ack_events.get(seq_num)
    while ack_event and not ack_event.is_set():
    # send to the world
        send_protobuf(amazon_socket, ua_commands)
        print("amazon truckarrived sequence number = {}".format(seq_num))
        ack_event.wait(10)
        if ack_event.is_set():
            print(f"Amazon ACK {seq_num} received, stopping retransmissions.")
            break
        else:
            print(f"Amazon ACK {seq_num} not received, timeout, resending...")
    print(f"Sent truck arrived {seq_num}")
    pass

def send_UADelivered(truck_id, tracking_id, seq_num, amazon_socket):
    delivered = amazon_ups_pb2.UADelivered()
    delivered.truckid = truck_id
    delivered.trackingid = tracking_id
    delivered.seqnum = seq_num

    ua_commands = amazon_ups_pb2.UACommands()
    ua_commands.delivered.append(delivered)

    ack_event = seq_amazon.ack_events.get(seq_num)
    # TO DO: accept acks
    while ack_event and not ack_event.is_set():
    # send to the world
        send_protobuf(amazon_socket, ua_commands)
        print("amazon uadelivered sequence number = {}".format(seq_num))
        ack_event.wait(10)
        if ack_event.is_set():
            print(f"Amazon ACK {seq_num} received, stopping retransmissions.")
        else:
            print(f"Amazon ACK {seq_num} not received, timeout, resending...")
    pass

def select_truck(db_pool):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT truckid FROM delivery_truck
                WHERE status = 0;
            """)
            trucks = cursor.fetchall()

            if not trucks:
                print("No trucks available with status 0.")
                return None
            
            selected_truck = random.choice(trucks)[0] 

            cursor.execute("""
                UPDATE delivery_truck
                SET status = 1
                WHERE truckid = %s;
            """, (selected_truck,))
            conn.commit() 

            print(f"Truck {selected_truck} status updated to 1.")
            return selected_truck
    
    except psycopg2.Error as e:
        conn.rollback() 
        print(f"Failed to select and update truck: {e}")
        return None
    finally:
        db_pool.putconn(conn)

def send_amazon_ack(socket, seq_num):
    ack_message = amazon_ups_pb2.UACommands()
    ack_message.acks.append(seq_num)
    send_protobuf(socket, ack_message)


# world
def process_uwresponse(message, db_pool, world_socket, amazon_socket):
    try:
        if message.completions:
            for completion in message.completions:
                # print(f"In uwresponse: \n{completion}")
                send_world_ack(world_socket, completion.seqnum)
                process_completion(completion, db_pool, amazon_socket)

        if message.delivered:
            for delivery in message.delivered:
                send_world_ack(world_socket, delivery.seqnum)
                process_delivery(delivery, db_pool, amazon_socket)

        if message.acks:
            for ack in message.acks:
                # TO DO: handle ack
                seq_world.acknowledge(ack)
                print(f"Acknowledgement received for world ack {ack}.")

        if message.truckstatus:
            for truck in message.truckstatus:
                send_world_ack(world_socket, truck.seqnum)
                process_truckstatus(truck, db_pool)

        if message.error:
            for err in message.error:
                send_world_ack(world_socket, err.seqnum)
                print(f"Error: {err.err} in response to message {err.originseqnum}")
        
        if message.HasField("finished"):
            if message.finished == True:
                # TO DO: close connection
                return
    except Exception as e:
        print(f"Error in uwresponse: {e}")

def process_completion(completion, db_pool, amazon_socket):
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE delivery_truck
                    SET x = %s, y = %s
                    WHERE truckid = %s
                    RETURNING status;
                """, (completion.x, completion.y, completion.truckid))
                current_status = cursor.fetchone()[0]
                cursor.execute("""
                        SELECT trackingid, warehouseid  
                        FROM delivery_order
                        WHERE truck_id = %s;
                    """, (completion.truckid, ))
                order_status = cursor.fetchone()
                if current_status == 1:
                    cursor.execute("""
                        UPDATE delivery_order
                        SET status = 1, loadTime = %s
                        WHERE truck_id = %s AND status = 0;
                    """, (datetime.now(), completion.truckid))
                    cursor.execute("""
                        UPDATE delivery_truck
                        SET status = 2
                        WHERE truckid = %s;
                    """, (completion.truckid,))

                    conn.commit()
                    # TO DO: send_UATruckArrived()
                    seq_num = seq_amazon.next()
                    send_UATruckArrived(completion.truckid, order_status[0], order_status[1], seq_num, amazon_socket)
                elif current_status == 3:
                    cursor.execute("""
                        UPDATE delivery_order
                        SET status = 3, completeTime = %s
                        WHERE truck_id = %s AND status = 2;
                    """, (datetime.now(), completion.truckid))

                    cursor.execute("""
                        UPDATE delivery_truck
                        SET status = 0
                        WHERE truckid = %s;
                    """, (completion.truckid,))
                    
                    conn.commit()
                    # TO DO: send_UADelivered()
                    seq_num = seq_amazon.next()
                    send_UADelivered(completion.truckid, order_status[0], seq_num, amazon_socket)

        except (Exception, psycopg2.DatabaseError) as e:
            print(f"Error in process_completion: {e}")
            conn.rollback()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Get database connection failed in process_completion: {e}")

def process_delivery(delivered, db_pool, amazon_socket):
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:

                select_order_stmt = """
                    SELECT trackingid FROM delivery_order
                    WHERE packageid = %s;
                """
                cursor.execute(select_order_stmt, (delivered.packageid,))
                tracking_id = cursor.fetchone()[0]

                update_order_stmt = """
                UPDATE delivery_order
                SET status = %s, completeTime = %s
                WHERE trackingid = %s AND truck_id = %s
                RETURNING trackingid;
                """
                cursor.execute(update_order_stmt, (3, datetime.now(), tracking_id, delivered.truckid))
                conn.commit()
                
                # TO DO: send_UADelivered(delivered)
                seq_num = seq_amazon.next()
                send_UADelivered(delivered.truckid, tracking_id, seq_num, amazon_socket)

        except psycopg2.Error as e:
            conn.rollback() 
            print(f"Error in process_delivery: {e}")
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Get database connection failed in process_delivered: {e}")

def process_truckstatus(truck, db_pool):
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                update_truck_stmt = """
                UPDATE delivery_truck
                SET status = %s, x = %s, y = %s
                WHERE truckid = %s;
                """
                cursor.execute(update_truck_stmt, (truck.status, truck.x, truck.y, truck.truckid))
                conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error in process_truckstatus: {e}")
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Get database connection failed in process_truckstatus: {e}")

def send_GoPickup(wh_id, truck_id, seq_num, world_socket, db_pool):
    try:
        message_gopick = world_ups_pb2.UGoPickup()
        message_gopick.truckid = truck_id
        message_gopick.whid = wh_id
        message_gopick.seqnum = seq_num

        message_command = world_ups_pb2.UCommands()
        message_command.pickups.add().CopyFrom(message_gopick)

        ack_event = seq_world.ack_events.get(seq_num)
        while ack_event and not ack_event.is_set():
        # send to the world
            send_protobuf(world_socket, message_command)
            print("world gopickup sequence number = {}".format(seq_num))
            ack_event.wait(10)
            if ack_event.is_set():
                print(f"World ACK {seq_num} received, stopping retransmissions.")
            else:
                print(f"World ACK {seq_num} not received, timeout, resending...")
        # TO DO: accept ack

        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                update_truck_stmt = """
                UPDATE delivery_truck
                SET status = %s
                WHERE truckid = %s;
                """
                cursor.execute(update_truck_stmt, (1, truck_id))
                conn.commit()
        except psycopg2.Error as e:
            print(f"Error in send_GoPickup: {e}")
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Get database connection failed in send_GoPickup: {e}")

def send_GoDeliver(truck_id, seq_num, world_socket, db_pool):
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT trackingid, destX, destY, packageid FROM delivery_order
                    WHERE truck_id = %s AND status = 1;  
                """, (truck_id,))
                
                orders = cursor.fetchall()
                delivery_locations = []
                for order in orders:
                    order_id, dest_x, dest_y, package_id = order
                    print(f"In GoDeliver: package_id: {package_id}")
                    delivery_location = world_ups_pb2.UDeliveryLocation()
                    delivery_location.packageid = package_id
                    delivery_location.x = dest_x
                    delivery_location.y = dest_y
                    delivery_locations.append(delivery_location)
                    
                    cursor.execute("""
                        UPDATE delivery_order
                        SET status = 2, deliveryTime = %s
                        WHERE trackingid = %s;
                    """, (datetime.now(), order_id))
        
                conn.commit()

                cursor.execute("""
                    UPDATE delivery_truck
                    SET status = 3
                    WHERE truckid = %s;
                """, (truck_id,))
                conn.commit()

            go_deliver = world_ups_pb2.UGoDeliver()
            go_deliver.truckid = truck_id
            go_deliver.seqnum = seq_num
            go_deliver.packages.extend(delivery_locations)

            ucommands = world_ups_pb2.UCommands()
            ucommands.deliveries.add().CopyFrom(go_deliver)

            # TO DO: accept acks
            ack_event = seq_world.ack_events.get(seq_num)
            while ack_event and not ack_event.is_set():
            # send to the world
                send_protobuf(world_socket, ucommands)
                print("world godeliver sequence number = {}".format(seq_num))
                ack_event.wait(10)
                if ack_event.is_set():
                    print(f"World ACK {seq_num} received, stopping retransmissions.")
                else:
                    print(f"World ACK {seq_num} not received, timeout, resending...")

        except psycopg2.Error as e:
            print(f"Database error in send_GoDeliver: {e}")
            conn.rollback()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Error in send_GoDeliver: {e}")


def send_world_ack(socket, seq_num):
    ack_message = world_ups_pb2.UCommands()
    ack_message.acks.append(seq_num)
    send_protobuf(socket, ack_message)
    print(f"world ack sent {seq_num}")