# from crypt import methods
from concurrent.futures import thread
from email.headerregistry import ContentTypeHeader
from flask import Flask
from flask import render_template, request
from collections import Counter
import os
import random
import requests
import json
import socket
import time
import threading
import json
import traceback

# FRONTEND APIS

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/registerPage', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/loginPage', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def blogs():
    if(request.method == 'POST'):
        with open('/data/Chat1.txt','r') as data:
            username = data.read().split('\n')
            firstname, lastname, email, pwd = username[-1].split()
            username = firstname + " " + lastname 
    return render_template('blogs.html', username=username)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def confirm():
    isLeader = env_values['isLeader']   
    if(isLeader == "True"):
        if(request.method == 'POST'):
            UserDetails = { 
            'name' : request.form['firstname'],
            'lastname' : request.form['lastname'],
            'email' : request.form['inputEmail'],
            'password' : request.form['inputPassword']
            }
            response1 = requests.post(url = 'http://Backupnode1:5555/register', headers={'Content-type': 'application/json'}, json = UserDetails)
            response2 = requests.post(url = 'http://Backupnode2:5555/register', headers={'Content-type': 'application/json'}, json = UserDetails)
            with open('/data/Chat1.txt','a') as data:
                name = request.form['firstname']
                lastname=request.form['lastname']
                email=request.form['inputEmail']
                password=request.form['inputPassword']
                data.write('\n')
                data.write(" " + name + " " + lastname + " " + email + " " + password)
            return render_template('index.html', message="User registered successfully!!! Please login to continue!")
    else:
        if(request.method == 'POST'):
            fileName = env_values['filesys']
            if request.headers.get('Content-Type') == "application/json" :
                with open("/data/" + fileName,'a') as data:
                    UserData = " "
                    for val in request.json.values():
                        UserData = UserData + val + " "
                    data.write('\n')
                    data.write(UserData)


# RAFT AND LEADER ELECTION



def requestVoteRPC():
    global r
    global nodes
    global env_values
    global nextIndex
    global matchIndex
    global lastApplied
    global commitIndex
    global log
    global currentTerm
    currentTerm = currentTerm+1
    candidate = env_values['name']
    env_values['status'] = "Candidate"
    env_values['votes'] = "1"
    targets = [node for node in nodes if node != env_values['name']]
    msg = {
        "sender_name": env_values['name'],
        "request": "VOTE_REQUEST",
        "term": currentTerm,
        "candidateId": env_values['name'],
        "lastLogIndex":len(log) - 1,
        "lastLogTerm": log[-1]['term'] if len(log)>0 else 0
    }
    msg_bytes = json.dumps(msg).encode()
    for node in targets:
        try:
            UDP_Socket.sendto(msg_bytes, (node, 5555))
        except:
            print("Failed to vote for " + node)
    r = threading.Timer(timeout, requestVoteRPC)
    r.start()
    return

def startElection():
    threading.Thread(target=requestVoteRPC, daemon=True).start()

def acknowledgeVote(decoded_msg):
    global r
    global nodes
    global env_values
    global nextIndex
    global matchIndex
    global lastApplied
    global commitIndex
    global log
    global currentTerm
    response = {'sender_name': env_values['name'], 'request': 'VOTE_ACK'}
    c_lastIndex = decoded_msg['lastLogIndex']
    c_lastTerm = decoded_msg['lastLogTerm']
    v_lastIndex = len(log) - 1
    v_lastTerm = log[-1]['term'] if len(log)>0 else 0
    
    if decoded_msg['term']<=currentTerm or v_lastTerm>c_lastTerm or (v_lastTerm==c_lastTerm and v_lastIndex>c_lastIndex):
        response['voted'] = False  
    else:
        currentTerm = decoded_msg['term']
        env_values['status'] = 'Follower'
        response['voted'] = True
        r = threading.Timer(timeout, requestVoteRPC)
        r.start()
    response_bytes = json.dumps(response).encode()
    try:
      UDP_Socket.sendto(response_bytes, (decoded_msg['sender_name'], 5555))
    except:
      print("Failed to acknowledge for " + decoded_msg['sender_name'])
    return
 
def listener():
    while True:
        try:
            msg, addr= UDP_Socket.recvfrom(1024)
        except:
            print(f"ERROR while fetching from socket : {traceback.print_exc()}")
 
        decoded_msg = json.loads(msg.decode('utf-8'))
        global r
        global nodes
        global env_values
        global nextIndex
        global matchIndex
        global lastApplied
        global commitIndex
        global log
        global currentTerm

        if int(env_values['isActive']) == 1:
            if "VOTE_REQUEST" in decoded_msg.values():
                if env_values['status'] == "Follower":
                    r.cancel()
                threading.Thread(target=acknowledgeVote, args=[decoded_msg], daemon=True).start()
       
            elif env_values['status'] == "Candidate" and "VOTE_ACK" in decoded_msg.values():
                env_values['votes'] = str(int(env_values['votes']) + int(decoded_msg['voted']))
                if int(env_values['votes']) >= 3:
                    r.cancel()
                    nextIndex = {}
                    matchIndex = {}
                    for node in nodes:
                        if node != env_values['name']:
                            nextIndex[node] = commitIndex + 1
                            matchIndex[node] = -1
                    env_values['status'] = "Leader"
                    env_values['votes'] = "0"
                    print("Elected leader is: ", env_values['name'])

            elif 'APPEND_RPC' in decoded_msg.values():
                r.cancel()
                print("Heartbeat from", decoded_msg['sender_name'])  
                threading.Thread(target=acknowledgeAppendRPC, args=[decoded_msg], daemon=True).start()             
                r = threading.Timer(timeout, requestVoteRPC)
                r.start()

            elif 'APPEND_ACK' in decoded_msg.values():
                threading.Thread(target=updateIndices, args=[decoded_msg], daemon=True).start()             

            elif 'CONVERT_FOLLOWER' in decoded_msg.values():
                print("----------CONVERTING FOLLOWER----------")
                env_values['status'] = 'Follower'
                r = threading.Timer(timeout, requestVoteRPC)
                r.start()

            elif 'LEADER_INFO' in decoded_msg.values():
                print("----------LEADER INFORMATION----------")
                print({'LEADER':env_values['current_leader']})

            elif 'TIMEOUT' in decoded_msg.values():
                print("----------TIMEOUT----------")
                r.cancel()
                threading.Thread(target=requestVoteRPC, daemon=True).start()

            elif 'SHUTDOWN' in decoded_msg.values():
                r.cancel()
                print("----------SHUTTING DOWN----------")
                env_values['isActive'] = "0"
                env_values['status'] = 'Follower'

            elif 'STORE' in decoded_msg.values():
                print("----------STORE----------")
                threading.Thread(target=store, args=[decoded_msg], daemon=True).start()

            elif 'RETRIEVE' in decoded_msg.values():
                print("----------RETRIEVE----------")
                threading.Thread(target=retrieve, daemon=True).start()
        
        elif 'RESTART' in decoded_msg.values():
            print("----------RESTART----------")
            env_values['status'] = 'Follower'
            currentTerm = 0
            env_values['isActive'] = "1"
            r = threading.Timer(timeout, requestVoteRPC)
            r.start()


 
def appendEntryRPC():
    global r
    global nodes
    global env_values
    global nextIndex
    global matchIndex
    global lastApplied
    global commitIndex
    global log
    global currentTerm
    while True:
        if env_values['status'] == 'Leader':
            targets = [node for node in nodes if node != env_values['name']]
            for node in targets:
                try:
                    message = {
                        'sender_name': env_values['name'],
                        'request': 'APPEND_RPC',
                        'term': currentTerm,
                        'leaderId': env_values['name'],
                        'prevLogIndex': nextIndex[node]-1,
                        'entry': log[nextIndex[node]:], #if (len(log)>nextIndex[fol] and log) else [],
                        'leaderCommit': commitIndex,
                        'prevLogTerm': log[nextIndex[node]-1]['term'] if (len(log) > 0 and nextIndex[node] >= 1) else 0
                    }
                    msg_bytes = json.dumps(message).encode()
                    UDP_Socket.sendto(msg_bytes, (node, 5555))
                except:
                    print("Failed to send append RPC to " + node)
            time.sleep(0.18)    
    return

def acknowledgeAppendRPC(decoded_msg):
    global r
    global nodes
    global env_values
    global nextIndex
    global matchIndex
    global lastApplied
    global commitIndex
    global log
    global currentTerm

    node = decoded_msg['sender_name']
    prevLogIndex = decoded_msg['prevLogIndex']
    prevLogTerm = decoded_msg['prevLogTerm']
    message = {
        'sender_name': env_values['name'],
        'request': 'APPEND_ACK',
        'success': None,
        'matchIndex': -1,
        'entry': decoded_msg['entry']
    }
    
    if decoded_msg['term'] < currentTerm:
        message['success'] = False
    elif prevLogIndex >= len(log):   
        env_values['current_leader'] = decoded_msg['sender_name'] 
        env_values['status'] = 'Follower'
        env_values['votes'] = '0'
        currentTerm = decoded_msg['term']
        message['success'] = False
        
    elif prevLogIndex>=0 and log[prevLogIndex]['term']!=prevLogTerm:
        env_values['current_leader'] = decoded_msg['sender_name']   
        env_values['status'] = 'Follower'
        env_values['votes'] = '0'
        currentTerm = decoded_msg['term']
        log = log[:prevLogIndex] 
        message['success'] = False 
    else:
        env_values['status'] = 'Follower'
        env_values['votes'] = '0'
        currentTerm = decoded_msg['term']
        env_values['current_leader'] = decoded_msg['sender_name']
        log[prevLogIndex+1:] = decoded_msg['entry']
        message['matchIndex'] = len(log) - 1
        message['success'] = True
        if decoded_msg['leaderCommit'] > commitIndex:
            commitIndex = min(decoded_msg['leaderCommit'], len(log)-1)
    
    message['term'] = currentTerm
    message = json.dumps(message).encode()
    try:
        UDP_Socket.sendto(message, (decoded_msg['sender_name'], 5555))
    except:
        print("Failed to send append RPC to " + node)
    return


def updateIndices(decoded_msg):
    global r
    global nodes
    global env_values
    global nextIndex
    global matchIndex
    global lastApplied
    global commitIndex
    global log
    global currentTerm

    node = decoded_msg['sender_name']
    
    if decoded_msg['success'] == True and matchIndex[node]!=decoded_msg['matchIndex']:
        if len(decoded_msg['entry']) > 0:
            nextIndex[node] += 1 
    elif decoded_msg['success'] == False:
        nextIndex[node] -= 1

    matchIndex[node] = decoded_msg['matchIndex']

    matchValues = list(matchIndex.values())
    matchValues_count = Counter(matchValues)
    mostCommonMatches = matchValues_count.most_common()
    mostCommon = []
    for match in mostCommonMatches:
        if match[1] == mostCommonMatches[0][1]:
            mostCommon.append(match[0])
    commitIndex = max(mostCommon)
    return

def retrieve():
    if env_values['status'] == 'Leader':
        message = {
            'sender_name': env_values['name'],
            'request': 'RETRIEVE',
            'term': None,
            'key': 'COMMITTED_LOGS',
            'value': log[:commitIndex+1]
        }
    else:
        message = {
            'sender_name': env_values['name'],
            'request': 'LEADER_INFO',
            'term': None,
            'key': 'LEADER',
            'value': env_values['current_leader']
        }
    msg_bytes = json.dumps(message).encode()
    try:
        UDP_Socket.sendto(msg_bytes, ("Controller", 5555))
    except:
        print("Failed to send retrieve to controller.")
    return

def store(decoded_msg):
    global log
    if env_values['status'] == 'Leader':
        entry = {}
        entry['term'] = currentTerm
        entry['key'] = decoded_msg['key']
        entry['value'] = decoded_msg['value']
        log.append(entry)
    else:
        message = {
            'sender_name': env_values['name'],
            'request': 'LEADER_INFO',
            'term': None,
            'key': 'LEADER',
            'value': env_values['current_leader']
        }
        msg_bytes = json.dumps(message).encode()
        try:
            UDP_Socket.sendto(msg_bytes, ("Controller", 5555))
        except:
            print("Failed to send store response to controller.")
    return

def commit():
    global r
    global nodes
    global env_values
    global nextIndex
    global matchIndex
    global lastApplied
    global commitIndex
    global log
    global currentTerm
    while True:
        if commitIndex > lastApplied:
            lastApplied += 1
            file = "/data/" + env_values['filesys']
            try:
                data = json.load(open(file))
            except:
                data = []
            finally:
                data.append(log[lastApplied])
                json.dump(data, open(file,'w'))
    return
       
 
if __name__ == '__main__': 
 
    env_values = os.environ
    timeout = random.randrange(550, 850)/1000
    currentTerm = 0
    nodes = ['Node1', 'Node2', 'Node3', 'Node4', 'Node5']
    candidate = None
    targets = []
    log = []
    commitIndex = -1
    lastApplied = -1

    nextIndex = {}
    matchIndex = {}
    for node in nodes:
        if node != env_values['name']:
            nextIndex[node] = commitIndex + 1
            matchIndex[node] = -1

    UDP_Socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDP_Socket.bind((env_values['name'], 5555))
 
    r = threading.Timer(timeout, startElection)
    r.start()
 
    threading.Thread(target=listener, daemon=True).start()
    threading.Thread(target=appendEntryRPC, daemon=True).start()
    threading.Thread(target=commit, daemon=True).start()
 
    while(True):
        pass
