# Libraries
import logging
from logging.handlers import RotatingFileHandler
import socket
import paramiko #ssh v2
import threading
import paramiko.rsakey
#Constants
logging_format= logging.Formatter("%(message)%")
SSH_BANNER='''

************************************************************************
*                                                                      *
*  Welcome to the Secure Shell (SSH) Server                            *
*                                                                      *
*  Server Version: OpenSSH_8.4p1                                       *
*                                                                      *
*  Unauthorized access to this system is prohibited.                   *
*  All activities on this system are monitored and recorded.            *
*  By accessing this system, you agree to comply with our policies.     *
*                                                                      *
*  For support, contact: support@example.com                           *
*                                                                      *
************************************************************************

'''

#host_key="server.key" #keep the key secret or local
host_key= paramiko.RSAKey(filename ="server.key")
# Loggers + Logging files
funnel_logger= logging.getLogger("FunnelLogger")
funnel_logger.setLevel=(logging.info)
funnel_handler= RotatingFileHandler("audits.log" , maxBytes=2000,backupCount=5)
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)


creds_logger= logging.getLogger("CredsLogger")
creds_logger.setLevel=(logging.info)
creds_handler= RotatingFileHandler("cmd_audits.log" , maxBytes=2000,backupCount=5)
creds_handler.setFormatter(logging_format)
creds_logger.addHandler(funnel_handler)

#Emulated shell
def emulated_shell(channel, client_ip):
    channel.send(b"corporate-jumpbox2$")
    command = b""
    while True:
        char = channel.recv(1)
        channel.send(char)
        if not char:
            channel.close()
        
        command+=char
        
        if char == b"/r":
            if command.strip() == b"exit":
                response= b"\n Goodbyte! \n"
                channel.close()
            elif command.strip() == b"pwd":
                response= b"\n"+ "\\usr\\local\\" + b"\r\n"
            elif command.strip() == b"whoami":
                response= b"\n" + b"corpuser1" + b"\r\n"
            elif command.strip() == b"ls":
                response= b"\n" + "jumpbox1.conf" + b"\r\n"
            elif command.strip() == b"cat jumpbox1.conf":
                response= b"\n" + "Go to deeboodah.com" + b"\r\n"
            else:
                response = b"\n" + bytes(command.strip()) + b"\r\n"

            
            channel.send(response)
            channel.send(b"corporate-jumpbox2$")
            channel=b""

#Shh server + sockets

class Server(paramiko.ServerInterface):
    
    def __init__(self, client_ip, input_username=None,input_password=None):
        self.event= threading.Event()
        self.client_ip=client_ip
        self.input_username= input_username
        self.input_password= input_password
        
    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        
    def get_allowed_auth(self):
        return "password"
    
    def check_auth_password(self, username, password):
        
        if self.input_username is not None and self.input_password is not None:
            if username == self.input_username and password == self.input_password:
                return paramiko.AUTH_SUCCESSFUL
            else:
                return paramiko.AUTH_FAILED
        else:
            return paramiko.AUTH_SUCCESSFUL
            
            
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
    
    def check_channel_exec_request(self, channel, command):
        command= str(command)
        return True
    
    @staticmethod
    def client_handle(client,addr,username,password):
        client_ip=addr[0]
        print(f"{client_ip} has connected to the server.")
        
        try:
            transport= paramiko.Transport(client)
            transport=local_version= SSH_BANNER
            server= Server(client_ip=client_ip, input_username=username,input_password=password)
            
            transport.add_server_key(host_key)
            transport.start_server(server=server)
            
            channel = transport.accept(100)
            if channel is None:
                print("No channel was opened.")
                
            standard_banner='''
                ************************************************************************
                *                                                                      *
                *  Server Version: OpenSSH_8.4p1                                       *
                *                                                                      *
                *  You have successfully logged in.                                    *
                *                                                                      *
                *  Please ensure you comply with our security policies.                *
                *  Unauthorized access is strictly prohibited.                         *
                *                                                                      *
                *  For support, contact: support@example.com                           *
                *                                                                      *
                ************************************************************************
                '''
            channel.send(standard_banner)
            emulated_shell(channel,client_ip=client_ip)  
        except Exception as error:
            print(error)
            print("!!!errorr!!!")
        finally:
            try:
                transport.close()
            except Exception as error:
                print(error)
                print("!!!error!!!")
            client.close()
            
    
#Provision SSH-based honeypot

def honeypot(address, port,username,password):
    socks= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socks.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    socks.bind((address,port))
    
    socks.listen(100)
    print(f"SSH server is listening on port {port}")
    
    while True:
        try:
            client,addr = socks.accept()
            ssh_honeypot_thread= threading.Thread(target=Server.client_handle, args=(client, addr,username,password))
            ssh_honeypot_thread.start()
            
        except Exception as error:
            print(error)
            
honeypot("127.0.0.1", 2223, "username", "password")