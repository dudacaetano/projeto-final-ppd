import tkinter as tk
from tkinter import ttk, messagebox
import xmlrpc.client
import paho.mqtt.client as mqtt
import threading
import time
import math
import random
"""
coordenad,as prox
Usuário 1:  São Paulo (Centro) → (23.550520, -46.633308)
Usuário 2: São Paulo (Próximo - 150m de distância) → (23.551520, -46.633808)


coordenadas dist
Usuário 1: São Paulo (Centro) → (23.550520, -46.633308)
Usuário 2: Guarulhos (Longe - 13km de distância) → (23.454167, -46.533333) 

Primeira posição (fora do alcance, mensagens são enfileiradas)

Usuário 1: Rio de Janeiro → (22.906847, -43.172896)
Usuário 2: Curitiba → (25.428356, -49.273251)

User1": (23.550520, -46.633308),  # São Paulo, Brasil
"User2": (35.676192, 139.650399),  # Tóquio, Japão
"""

class ClienteChat:
    def __init__(self):
        # Inicialização da janela principal
        self.root = tk.Tk()
        self.root.title("Chat com Localização")
        
        # Variáveis de estado
        self.nome = ""
        self.lat = 0
        self.lon = 0
        
        # Estruturas de dados para melhorias
        self.usuarios_conhecidos = {}  # Dicionário para armazenar todos os usuários
        self.usuarios_proximos = []    # Lista para usuários próximos
        self.mensagens_pendentes = {}  # Dicionário para mensagens pendentes
        
        # Configurar interface
        self.criar_interface()
        
        # Conectar ao servidor
        self.servidor_rpc = xmlrpc.client.ServerProxy("http://localhost:8000")
        
        # Configurar MQTT com broker público
        self.mqtt_client = mqtt.Client(
            client_id=f'cliente_chat_{random.randint(1000,9999)}',
            protocol=mqtt.MQTTv311
        )
        
        # Configurar callbacks do MQTT
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        # Configurar broker público
        self.BROKER = "test.mosquitto.org"
        self.PORT = 1883
        
        # Conectar ao broker público
        self.mqtt_client.connect(self.BROKER, self.PORT, 60)
        self.mqtt_client.loop_start()
        
        # Iniciar thread de atualização de usuários e localização
        self.atualizar_thread = threading.Thread(target=self.atualizar_periodicamente)
        self.atualizar_thread.daemon = True
        self.atualizar_thread.start()

    def criar_interface(self):
        # Frame de login
        frame_login = ttk.Frame(self.root, padding="10")
        frame_login.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame_login, text="Nome:").grid(row=0, column=0)
        self.entrada_nome = ttk.Entry(frame_login)
        self.entrada_nome.grid(row=0, column=1)
        
        # Campos de coordenadas com botões de atualização
        ttk.Label(frame_login, text="Latitude:").grid(row=1, column=0)
        self.entrada_lat = ttk.Entry(frame_login)
        self.entrada_lat.grid(row=1, column=1)
        ttk.Button(frame_login, text="Atualizar Lat",
                  command=lambda: self.atualizar_posicao('lat')).grid(row=1, column=2)
        
        ttk.Label(frame_login, text="Longitude:").grid(row=2, column=0)
        self.entrada_lon = ttk.Entry(frame_login)
        self.entrada_lon.grid(row=2, column=1)
        ttk.Button(frame_login, text="Atualizar Lon",
                  command=lambda: self.atualizar_posicao('lon')).grid(row=2, column=2)
        
        ttk.Button(frame_login, text="Conectar",
                  command=self.conectar).grid(row=3, column=0, columnspan=3)
        
        # Frame do chat
        self.frame_chat = ttk.Frame(self.root, padding="10")
        self.frame_chat.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.lista_usuarios = tk.Listbox(self.frame_chat, height=10)
        self.lista_usuarios.grid(row=0, column=0, columnspan=2)
        
        self.entrada_mensagem = ttk.Entry(self.frame_chat)
        self.entrada_mensagem.grid(row=1, column=0)
        
        ttk.Button(self.frame_chat, text="Enviar",
                  command=self.enviar_mensagem).grid(row=1, column=1)
        
        self.texto_chat = tk.Text(self.frame_chat, height=10, width=40)
        self.texto_chat.grid(row=2, column=0, columnspan=2)

    def atualizar_posicao(self, coordenada):
        """Atualiza a posição do usuário e notifica o servidor"""
        try:
            if coordenada == 'lat':
                nova_lat = float(self.entrada_lat.get())
                self.lat = nova_lat
                self.servidor_rpc.atualizar_localizacao(self.nome, self.lat, self.lon)
                messagebox.showinfo("Sucesso",
                                  f"Latitude atualizada para {nova_lat}")
            else:
                nova_lon = float(self.entrada_lon.get())
                self.lon = nova_lon
                self.servidor_rpc.atualizar_localizacao(self.nome, self.lat, self.lon)
                messagebox.showinfo("Sucesso",
                                  f"Longitude atualizada para {nova_lon}")
            self.atualizar_usuarios()
        except ValueError:
            messagebox.showerror("Erro",
                               "Por favor, insira um valor numérico válido")

    def calcular_distancia_euclidiana(self, lat1, lon1, lat2, lon2):
        """Calcula distância euclidiana entre dois pontos"""
        dx = lat2 - lat1
        dy = lon2 - lon1
        return math.sqrt(dx * dx + dy * dy)

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print("Conectado ao broker com sucesso")
        else:
            print(f"Falha na conexão: código {reason_code}")

    def on_disconnect(self, client, userdata, reason_code, properties=None):
        print(f"Desconectado do broker. Código: {reason_code}")
        if reason_code != 0:
            self.mqtt_client.reconnect()

    def on_message(self, client, userdata, msg):
        remetente, mensagem = msg.payload.decode().split(":", 1)
        self.texto_chat.insert(tk.END, f"{remetente}: {mensagem}\n")
        self.texto_chat.see(tk.END)

    def conectar(self):
        self.nome = self.entrada_nome.get()
        try:
            self.lat = float(self.entrada_lat.get())
            self.lon = float(self.entrada_lon.get())
            
            if self.servidor_rpc.registrar_usuario(self.nome, self.lat, self.lon):
                self.mqtt_client.subscribe(f"chat/{self.nome}")
                self.frame_chat.tkraise()
                self.atualizar_usuarios()
            else:
                messagebox.showerror("Erro",
                                   "Não foi possível conectar ao servidor")
                
        except ValueError:
            messagebox.showerror("Erro",
                               "Por favor, insira valores numéricos válidos para latitude e longitude")

    def atualizar_periodicamente(self):
        while True:
            if self.nome:
                self.servidor_rpc.atualizar_localizacao(self.nome, self.lat, self.lon)
                self.atualizar_usuarios()
                self.verificar_mensagens_pendentes()
            time.sleep(30)

    def verificar_mensagens_pendentes(self):
        """Verifica se há mensagens pendentes que podem ser entregues"""
        usuarios_proximos = self.servidor_rpc.encontrar_usuarios_proximos(self.nome)
        
        for usuario in usuarios_proximos:
            if usuario in self.mensagens_pendentes:
                for msg in self.mensagens_pendentes[usuario][:]:
                    self.mqtt_client.publish(f"chat/{usuario}",
                                           f"{self.nome}:{msg}")
                    self.mensagens_pendentes[usuario].remove(msg)

    def atualizar_usuarios(self):
        try:
            # Obter lista atual de usuários próximos
            usuarios_proximos = self.servidor_rpc.encontrar_usuarios_proximos(self.nome)
            
            # Atualizar dicionário de usuários conhecidos
            for usuario in usuarios_proximos:
                self.usuarios_conhecidos[usuario] = True
            
            # Limpar lista de exibição
            self.lista_usuarios.delete(0, tk.END)
            
            # Primeiro, adicionar usuários próximos em destaque
            for usuario in usuarios_proximos:
                self.lista_usuarios.insert(tk.END, f"[PRÓXIMO] {usuario}")
            
            # Depois, adicionar outros usuários conhecidos
            usuarios_distantes = [
                u for u in self.usuarios_conhecidos 
                if u not in usuarios_proximos
            ]
            for usuario in usuarios_distantes:
                self.lista_usuarios.insert(tk.END, usuario)
                
        except Exception as e:
            print(f"Erro ao atualizar lista de usuários: {str(e)}")
            self.lista_usuarios.delete(0, tk.END)

    def enviar_mensagem(self):
        try:
            destinatario = self.lista_usuarios.get(self.lista_usuarios.curselection())
            # Remover marcadores [PRÓXIMO] se existir
            destinatario = destinatario.replace("[PRÓXIMO] ", "")
            mensagem = self.entrada_mensagem.get()
            
            if destinatario:
                # Tentar enviar mensagem diretamente
                if self.servidor_rpc.enviar_mensagem(self.nome, destinatario, mensagem):
                    self.texto_chat.insert(tk.END, f"Você: {mensagem}\n")
                else:
                    # Se falhar, armazenar para entrega posterior
                    if destinatario not in self.mensagens_pendentes:
                        self.mensagens_pendentes[destinatario] = []
                    self.mensagens_pendentes[destinatario].append(mensagem)
                    messagebox.showinfo("Mensagem Enfileirada",
                                      "Destinatário não está no alcance. Mensagem será entregue quando próximo.")
                
                self.entrada_mensagem.delete(0, tk.END)
            else:
                messagebox.showwarning("Atenção",
                                     "Selecione um destinatário antes de enviar uma mensagem.")
                
        except tk.TclError:
            messagebox.showwarning("Atenção",
                                 "Selecione um destinatário antes de enviar uma mensagem.")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ClienteChat()
    app.run()