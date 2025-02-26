import paho.mqtt.client as mqtt
import xmlrpc.server
import json
import math
import time
import threading

'''
Distancia euclidiana 

x = Ax, Bx
Y = Ay, By 

Dist(AB)= sqrt((Bx - Ax)^2 + (By - Ay)^2)
'''


class ServidorChat:
    def __init__(self):
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.BROKER = "test.mosquitto.org"
        self.PORT = 1883
        self.mqtt_client.connect(self.BROKER, self.PORT, 60)
        self.mqtt_client.loop_start()
        
        self.usuarios = {}
        self.mensagens_pendentes = self.carregar_mensagens()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print("Conectado ao broker") if reason_code == 0 else print(f"Falha na conexão: {reason_code}")
    
    def on_disconnect(self, client, userdata, reason_code, properties):
        print(f"Desconectado do broker. Código: {reason_code}")
        if reason_code != 0:
            time.sleep(5)
            self.mqtt_client.reconnect()
    
    def salvar_mensagens(self):
        with open("mensagens_pendentes.json", "w") as f:
            json.dump(self.mensagens_pendentes, f)

    def carregar_mensagens(self):
        try:
            with open("mensagens_pendentes.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def calcular_distancia(self, lat1, lon1, lat2, lon2):
        return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
    
    def registrar_usuario(self, nome, lat, lon):
        self.usuarios[nome] = (lat, lon)
        self.verificar_mensagens_pendentes(nome)
        return True
    
    def atualizar_localizacao(self, nome, lat, lon):
        if nome in self.usuarios:
            self.usuarios[nome] = (lat, lon)
            self.verificar_mensagens_pendentes(nome)
            return True
        return False
    
    def encontrar_usuarios_proximos(self, nome):
        if nome not in self.usuarios:
            return []
        lat, lon = self.usuarios[nome]
        return [u for u, (ul, un) in self.usuarios.items() if u != nome and self.calcular_distancia(lat, lon, ul, un) <= 200]
    
    def enviar_mensagem(self, remetente, destinatario, mensagem):
        if destinatario not in self.usuarios:
            return False
        
        lat1, lon1 = self.usuarios[remetente]
        lat2, lon2 = self.usuarios[destinatario]
        
        if self.calcular_distancia(lat1, lon1, lat2, lon2) <= 200:
            self.mqtt_client.publish(f"chat/{destinatario}", f"{remetente}:{mensagem}")
            return True
        else:
            if destinatario not in self.mensagens_pendentes:
                self.mensagens_pendentes[destinatario] = []
            self.mensagens_pendentes[destinatario].append((remetente, mensagem))
            self.salvar_mensagens()
            return False
    
    def verificar_mensagens_pendentes(self, usuario):
        if usuario in self.mensagens_pendentes:
            for remetente, mensagem in self.mensagens_pendentes[usuario]:
                self.mqtt_client.publish(f"chat/{usuario}", f"{remetente}:{mensagem}")
            del self.mensagens_pendentes[usuario]
            self.salvar_mensagens()

servidor = xmlrpc.server.SimpleXMLRPCServer(("localhost", 8000))
servidor_chat = ServidorChat()
servidor.register_instance(servidor_chat)

# Atualização periódica para verificar mensagens pendentes

def atualizar_posicoes_periodicamente():
    while True:
        for nome in list(servidor_chat.usuarios.keys()):
            lat, lon = servidor_chat.usuarios[nome]
            servidor_chat.atualizar_localizacao(nome, lat, lon)
        time.sleep(120)  # A cada 2 minutos

threading.Thread(target=atualizar_posicoes_periodicamente, daemon=True).start()

servidor.serve_forever()
