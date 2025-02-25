# servidor.py
import paho.mqtt.client as mqtt
import xmlrpc.server
from queue import Queue
import math
import threading
import time

class ServidorChat:
    def __init__(self):
        # Configurar cliente MQTT com versão 2 da API
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        # Configurar broker público sem TLS
        self.BROKER = "test.mosquitto.org"  # Definir como variável de instância
        self.PORT = 1883
        
        # Conectar ao broker
        self.mqtt_client.connect(self.BROKER, self.PORT, 60)
        self.mqtt_client.loop_start()
        
        self.usuarios = {}
        self.mensagens_pendentes = {}
        
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"Conectado ao broker {self.BROKER} com sucesso")
        else:
            print(f"Falha na conexão: código {reason_code}")
            
    def on_disconnect(self, client, userdata, reason_code, properties):
        print(f"Desconectado do broker. Código: {reason_code}")
        if reason_code != 0:
            self.reconectar()
            
    def reconectar(self):
        while True:
            try:
                self.mqtt_client.reconnect()
                break
            except Exception as e:
                print(f"Tentativa de reconexão falhou: {e}")
                time.sleep(5)
                
    def registrar_usuario(self, nome, lat, lon):
        self.usuarios[nome] = (lat, lon)
        return True
        
    def atualizar_localizacao(self, nome, lat, lon):
        if nome in self.usuarios:
            self.usuarios[nome] = (lat, lon)
            self.verificar_mensagens_pendentes(nome)
            return True
        return False
        
    def calcular_distancia(self, lat1, lon1, lat2, lon2):
        return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
        
    def encontrar_usuarios_proximos(self, nome):
        lat, lon = self.usuarios[nome]
        proximos = []
        for outro_nome, (out_lat, out_lon) in self.usuarios.items():
            if outro_nome != nome:
                distancia = self.calcular_distancia(lat, lon, out_lat, out_lon)
                if distancia <= 200:
                    proximos.append(outro_nome)
        return proximos
        
    def enviar_mensagem(self, remetente, destinatario, mensagem):
        if destinatario in self.usuarios:
            self.mqtt_client.publish(f"chat/{destinatario}", f"{remetente}:{mensagem}")
            return True
        else:
            if destinatario not in self.mensagens_pendentes:
                self.mensagens_pendentes[destinatario] = []
            self.mensagens_pendentes[destinatario].append((remetente, mensagem))
            return False
        
    def verificar_mensagens_pendentes(self, usuario):
        if usuario in self.mensagens_pendentes:
            for remetente, mensagem in self.mensagens_pendentes[usuario]:
                self.mqtt_client.publish(f"chat/{usuario}", f"{remetente}:{mensagem}")
            del self.mensagens_pendentes[usuario]

# Iniciar servidor XML-RPC
servidor = xmlrpc.server.SimpleXMLRPCServer(("localhost", 8000))
servidor_chat = ServidorChat()
servidor.register_instance(servidor_chat)
servidor.serve_forever()