import paho.mqtt.client as mqtt
import xmlrpc.server
import json
import math
import time
from datetime import datetime
import random

'''
Distancia euclidiana 

x = Ax, Bx
Y = Ay, By 

Dist(AB)= sqrt((Bx - Ax)^2 + (By - Ay)^2)
'''
class ServidorChat:
    def __init__(self):
        # Configurar callbacks primeiro
        self.on_connect = self._on_connect
        self.on_disconnect = self._on_disconnect
        
        # Configuração do cliente MQTT usando broker público
        self.BROKER = "test.mosquitto.org"
        self.PORT = 1883
        self.mqtt_client = mqtt.Client(
            client_id=f'servidor_chat_{random.randint(1000,9999)}',
            protocol=mqtt.MQTTv311
        )
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        # Configuração do servidor XML-RPC
        self.xmlrpc_server = xmlrpc.server.SimpleXMLRPCServer(
            ('localhost', 8000),
            allow_none=True,
            use_builtin_types=True
        )
        
        # Registra as funções XML-RPC
        self.xmlrpc_server.register_instance(self)
        
        # Inicializa estruturas de dados
        self.usuarios = {}  # Armazena as coordenadas dos usuários
        self.usuarios_conhecidos = {}  # Armazena todos os usuários já detectados
        self.mensagens_pendentes = {}  # Armazena mensagens pendentes
        
        # Conecta ao broker MQTT público
        self.mqtt_client.connect(self.BROKER, self.PORT, 60)
        self.mqtt_client.loop_start()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Callback quando conectado ao broker MQTT"""
        if reason_code == 0:
            print(f"{datetime.now()} - Conectado ao broker com sucesso")
        else:
            print(f"{datetime.now()} - Falha na conexão MQTT: {reason_code}")

    def _on_disconnect(self, client, userdata, reason_code, properties=None):
        """Callback quando desconectado do broker MQTT"""
        print(f"{datetime.now()} - Desconectado do broker MQTT. Código: {reason_code}")
        if reason_code != 0:
            self.mqtt_client.reconnect()

    def encontrar_usuarios_proximos(self, nome):
        """Encontra usuários próximos ao usuário especificado"""
        if nome not in self.usuarios:
            return []  # Retorna lista vazia se usuário não existir
        
        # Atualiza dicionário de usuários conhecidos
        for outro_usuario in self.usuarios:
            self.usuarios_conhecidos[outro_usuario] = True
            
        usuarios_proximos = []
        usuario_atual = self.usuarios[nome]
        
        for outro_usuario, coordenadas in self.usuarios.items():
            if outro_usuario != nome:
                try:
                    distancia = self.calcular_distancia_euclidiana(
                        usuario_atual[0], usuario_atual[1],
                        coordenadas[0], coordenadas[1]
                    )
                    if distancia <= 200:  # Limite de 200 metros
                        usuarios_proximos.append(outro_usuario)
                except Exception as e:
                    print(f"Erro ao calcular distância para {outro_usuario}: {str(e)}")
        
        return usuarios_proximos

    def calcular_distancia_euclidiana(self, lat1, lon1, lat2, lon2):
        """Calcula distância euclidiana entre dois pontos"""
        METROS_POR_GRAU = 111320  # Aproximadamente metros por grau
        d_lat = (lat2 - lat1) * METROS_POR_GRAU
        d_lon = (lon2 - lon1) * METROS_POR_GRAU
        return math.sqrt(d_lat**2 + d_lon**2)

    def registrar_usuario(self, nome, lat, lon):
        """Função XML-RPC para registrar um usuário"""
        self.usuarios[nome] = (lat, lon)
        self.usuarios_conhecidos[nome] = True
        self.verificar_mensagens_pendentes(nome)
        return True

    def atualizar_localizacao(self, nome, lat, lon):
        """Função XML-RPC para atualizar localização de um usuário"""
        if nome in self.usuarios:
            self.usuarios[nome] = (lat, lon)
            self.verificar_mensagens_pendentes(nome)
            return True
        return False

    def enviar_mensagem(self, remetente, destinatario, mensagem):
        """Função XML-RPC para enviar mensagem entre usuários"""
        if destinatario not in self.usuarios:
            return False
            
        lat1, lon1 = self.usuarios[remetente]
        lat2, lon2 = self.usuarios[destinatario]
        
        # Calcula distância usando fórmula euclidiana
        distancia = self.calcular_distancia_euclidiana(lat1, lon1, lat2, lon2)
        
        if distancia <= 200:  # Limite de 200 metros
            self.mqtt_client.publish(f"chat/{destinatario}",
                json.dumps({
                    'remetente': remetente,
                    'mensagem': mensagem,
                    'timestamp': datetime.now().isoformat()
                }))
            return True
        else:
            # Armazena mensagem pendente
            if destinatario not in self.mensagens_pendentes:
                self.mensagens_pendentes[destinatario] = []
            
            self.mensagens_pendentes[destinatario].append({
                'remetente': remetente,
                'mensagem': mensagem,
                'timestamp': datetime.now().isoformat()
            })
            return False

    def verificar_mensagens_pendentes(self, usuario):
        """Verifica e entrega mensagens pendentes para um usuário"""
        if usuario not in self.mensagens_pendentes:
            return
            
        mensagens_pendentes = self.mensagens_pendentes[usuario]
        for msg in mensagens_pendentes[:]:  # Itera sobre uma cópia da lista
            remetente = msg['remetente']
            lat1, lon1 = self.usuarios[usuario]
            lat2, lon2 = self.usuarios[remetente]
            
            distancia = self.calcular_distancia_euclidiana(lat1, lon1, lat2, lon2)
            if distancia <= 200:
                self.mqtt_client.publish(f"chat/{usuario}",
                    json.dumps(msg))
                self.mensagens_pendentes[usuario].remove(msg)

    def iniciar(self):
        """Inicia o servidor XML-RPC e o loop MQTT"""
        print(f"{datetime.now()} - Iniciando servidor XML-RPC na porta 8000")
        self.xmlrpc_server.serve_forever()

if __name__ == "__main__":
    servidor = ServidorChat()
    servidor.iniciar()