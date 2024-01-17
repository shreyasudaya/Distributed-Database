import json
import socket
import traceback
import time
import threading
import sys
import os

target = sys.argv[1]
request = sys.argv[2]

# Wait following seconds below sending the controller request
time.sleep(5)

# Read Message Template
msg = json.load(open("Message.json"))

# Initialize
sender = "Controller"
#target = "Node1"
port = 5555

# Request
msg['sender_name'] = sender
msg['request'] = request
if request=='STORE':
    msg['key'] = sys.argv[3]
    msg['value'] = sys.argv[4]
print(f"Request Created : {msg}")

# Socket Creation and Binding
skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
skt.bind((sender, port))

nodes = ['Node1', 'Node2', 'Node3', 'Node4', 'Node5']

# Send Message
try:
    if request != 'PRINT_LOGS':
        skt.sendto(json.dumps(msg).encode('utf-8'), (target, port))
    else:
        for n in nodes:
            skt.sendto(json.dumps(msg).encode('utf-8'), (n, port))
except:
    print(f"ERROR WHILE SENDING REQUEST ACROSS : {traceback.format_exc()}")

def stop():
    os._exit(0)

t = threading.Timer(5, stop)
t.start()

while True:
    try:
        msg, addr = skt.recvfrom(1024)
    except:
        print(f"ERROR while fetching from socket : {traceback.print_exc()}")

    # Decoding the Message received
    decoded_msg = json.loads(msg.decode('utf-8'))

    print(decoded_msg)
    
    if decoded_msg:
        t.cancel()
        break

