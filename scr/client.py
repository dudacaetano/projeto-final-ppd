from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from geopy.distance import distance
import time
import threading
import redis

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Redis para armazenar mensagens
r = redis.Redis(host='localhost', port=6379, db=0)

# Armazenar usuários
users = {}

def refresh_users():
    while True:
        time.sleep(120)  # Espera 2 minutos
        for user_id, user_info in users.items():
            # Atualiza a lista de usuários visíveis
            emit('update_users', get_nearby_users(user_info['location']), room=user_id)

def get_nearby_users(location):
    nearby_users = []
    for uid, info in users.items():
        if uid != location['user_id']:
            dist = distance(location['coords'], info['location']['coords']).meters
            if dist <= 200:
                nearby_users.append({'user_id': uid, 'name': info['name'], 'location': info['location']})
    return nearby_users

@socketio.on('register')
def register(data):
    user_id = data['user_id']
    name = data['name']
    location = {'coords': (data['latitude'], data['longitude'])}
    
    users[user_id] = {'name': name, 'location': location}
    emit('user_registered', {'user_id': user_id, 'name': name}, broadcast=True)
    emit('update_users', get_nearby_users(location), room=user_id)

@socketio.on('update_location')
def update_location(data):
    user_id = data['user_id']
    new_location = {'coords': (data['latitude'], data['longitude'])}
    
    if user_id in users:
        users[user_id]['location'] = new_location
        emit('update_users', get_nearby_users(new_location), room=user_id)

@socketio.on('send_message')
def send_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    message = data['message']
    
    if receiver_id in users:
        receiver_location = users[receiver_id]['location']
        sender_location = users[sender_id]['location']
        
        dist = distance(sender_location['coords'], receiver_location['coords']).meters
        if dist <= 200:
            emit('receive_message', {'sender_id': sender_id, 'message': message}, room=receiver_id)
        else:
            # Armazena a mensagem na fila
            r.lpush(f'messages:{receiver_id}', f"{sender_id}:{message}")

@socketio.on('check_messages')
def check_messages(data):
    user_id = data['user_id']
    while True:
        message = r.rpop(f'messages:{user_id}')
        if message:
            sender_id, message_content = message.decode('utf-8').split(':', 1)
            emit('receive_message', {'sender_id': sender_id, 'message': message_content}, room=user_id)
        else:
            break

if __name__ == '__main__':
    threading.Thread(target=refresh_users, daemon=True).start()
    socketio.run(app, debug=True)