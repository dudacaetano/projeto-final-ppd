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

import tkinter as tk
from tkinter import ttk, messagebox
import xmlrpc.client
import paho.mqtt.client as mqtt
import threading
import time

class ClienteChat:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat com Localização")
        self.nome = ""
        self.lat = 0
        self.lon = 0
        
        # Configurar interface
        self.criar_interface()
        
        # Conectar ao servidor
        self.servidor_rpc = xmlrpc.client.ServerProxy("http://localhost:8000")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        # Configurar broker público
        self.BROKER = "test.mosquitto.org"
        self.PORT = 1883
        
        self.mqtt_client.connect(self.BROKER, self.PORT, 60)
        self.mqtt_client.loop_start()
        
        # Iniciar thread de atualização de usuários e localização
        self.atualizar_thread = threading.Thread(target=self.atualizar_periodicamente)
        self.atualizar_thread.daemon = True
        self.atualizar_thread.start()
        
    def criar_interface(self):
        frame_login = ttk.Frame(self.root, padding="10")
        frame_login.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame_login, text="Nome:").grid(row=0, column=0)
        self.entrada_nome = ttk.Entry(frame_login)
        self.entrada_nome.grid(row=0, column=1)
        
        ttk.Label(frame_login, text="Latitude:").grid(row=1, column=0)
        self.entrada_lat = ttk.Entry(frame_login)
        self.entrada_lat.grid(row=1, column=1)
        
        ttk.Label(frame_login, text="Longitude:").grid(row=2, column=0)
        self.entrada_lon = ttk.Entry(frame_login)
        self.entrada_lon.grid(row=2, column=1)
        
        ttk.Button(frame_login, text="Conectar", command=self.conectar).grid(row=3, column=0, columnspan=2)
        
        self.frame_chat = ttk.Frame(self.root, padding="10")
        self.frame_chat.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.lista_usuarios = tk.Listbox(self.frame_chat, height=10)
        self.lista_usuarios.grid(row=0, column=0, columnspan=2)
        
        self.entrada_mensagem = ttk.Entry(self.frame_chat)
        self.entrada_mensagem.grid(row=1, column=0)
        
        ttk.Button(self.frame_chat, text="Enviar", command=self.enviar_mensagem).grid(row=1, column=1)
        
        self.texto_chat = tk.Text(self.frame_chat, height=10, width=40)
        self.texto_chat.grid(row=2, column=0, columnspan=2)
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Conectado ao broker com sucesso")
        else:
            print(f"Falha na conexão: código {reason_code}")
        
    def on_disconnect(self, client, userdata, reason_code, properties):
        print(f"Desconectado do broker. Código: {reason_code}")
        if reason_code != 0:
            self.mqtt_client.reconnect()
            
    def conectar(self):
        self.nome = self.entrada_nome.get()
        self.lat = float(self.entrada_lat.get())
        self.lon = float(self.entrada_lon.get())
        
        if self.servidor_rpc.registrar_usuario(self.nome, self.lat, self.lon):
            self.mqtt_client.subscribe(f"chat/{self.nome}")
            self.frame_chat.tkraise()
            self.atualizar_usuarios()
        else:
            messagebox.showerror("Erro", "Não foi possível conectar ao servidor")
            
    def on_message(self, client, userdata, msg):
        remetente, mensagem = msg.payload.decode().split(":", 1)
        self.texto_chat.insert(tk.END, f"{remetente}: {mensagem}\n")
        self.texto_chat.see(tk.END)
        
    def atualizar_periodicamente(self):
        while True:
            if self.nome:
                self.servidor_rpc.atualizar_localizacao(self.nome, self.lat, self.lon)
                self.atualizar_usuarios()
            time.sleep(120)
            
    def atualizar_usuarios(self):
        usuarios_proximos = self.servidor_rpc.encontrar_usuarios_proximos(self.nome)
        self.lista_usuarios.delete(0, tk.END)
        for usuario in usuarios_proximos:
            self.lista_usuarios.insert(tk.END, usuario)
            
    def enviar_mensagem(self):
        try:
            destinatario = self.lista_usuarios.get(self.lista_usuarios.curselection())
            mensagem = self.entrada_mensagem.get()
            if destinatario:
                if self.servidor_rpc.enviar_mensagem(self.nome, destinatario, mensagem):
                    self.texto_chat.insert(tk.END, f"Você: {mensagem}\n")
                else:
                    messagebox.showinfo("Mensagem Enfileirada", "Destinatário não está no alcance. Mensagem será entregue quando próximo.")
                self.entrada_mensagem.delete(0, tk.END)
        except tk.TclError:
            messagebox.showwarning("Atenção", "Selecione um destinatário antes de enviar uma mensagem.")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ClienteChat()
    app.run()
