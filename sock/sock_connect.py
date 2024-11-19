import socket
import time
import logging


class Socket:

    def connect(self, timeout=5):
        socket.setdefaulttimeout(timeout)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)		
        self.sock.connect((self.server_ip_address, self.server_port))
        self.status_connect = True

    def disconnect(self):
        self.sock.close()

    def decipher_answer_for_radiation(self):
            radiation_hex = self._response_hex[6:14] 
            radiation_reversed = ''.join([radiation_hex[i:i+2] for i in range(0, len(radiation_hex), 2)][::-1])  # 0000000E
            print(radiation_reversed)
            radiation_value = int(radiation_reversed, 16) 
            return radiation_value * 0.01


    def send_request_hex(self, bytes_request: str = '55AA01') -> bool:
        try:
            hex_data = bytes.fromhex(bytes_request)
            
            self.sock.sendall(hex_data)
            time.sleep(1)

            response = self.sock.recv(1024).hex()
            size = len(response)
            print("Розмір отриманих даних:", size)
            print("Отримані дані:", response)

            self._response_hex = response
            return True
        except Exception as e:
            print(f"Сталася помилка: {e}")
            return False


    def __init__(self, server_ip_address = None, server_port = None):
        self.server_ip_address = server_ip_address
        self.server_port = server_port
        self.sock = None
        self._response_hex = None
        self.status_connect = False

        try:
            self.connect()
        except Exception as e:
            print(f"Error: {e}")