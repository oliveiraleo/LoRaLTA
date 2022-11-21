import socket #adds socket connection support
import time
import serial #adds serial connection support
import pynmea2 #adds NMEA parsing support
from datetime import datetime
import traceback #required to get the stack trace
import re #required to use regex operations
import csv #to save files
import requests #required for API query

"""
Some useful messages are commented out with the TAG #DEBUG
They were commented to avoid console pollution
"""

class LoraEndDevice:
    def __init__(self):

        self.loraSerial = serial.Serial()
        self.loraSerial.port = '/dev/ttyUSB0'
        self.loraSerial.baudrate = 115200
        self.loraSerial.bytesize = 8
        self.loraSerial.parity='N'
        self.loraSerial.stopbits=1
        self.loraSerial.timeout=2
        self.loraSerial.rtscts=False
        self.loraSerial.xonxoff=False

        self.lastAtCmdRx = ''

    def setPortCom(self, newPort):
        self.loraSerial.port = newPort

    def openSerialPort(self):
        self.loraSerial.open()

    def closeSerialPort(self):
        self.loraSerial.close()

    # resets the serial connection
    def resetSerialPort(self):
        #it clears the connection buffer
        self.closeSerialPort()
        time.sleep(2)
        self.openSerialPort()

    # sends a command to the device
    def sendCmdAt(self,cmd):
        if self.loraSerial.is_open:
            self.loraSerial.write(cmd.encode())
        else:
            print("[ERROR] It\'s not possible to communicate with LoRa module!")

    def getAtAnswer(self):
        self.lastAtCmdRx = self.loraSerial.read(100)

    # prints the answer of device's serial port (i.e. the messages you see when using minicom)
    def printLstAnswer(self):
        print(self.lastAtCmdRx.decode('UTF-8'))
    
    # gets the answer of device's serial port (i.e. the messages you see when using minicom)
    def getLstAnswer(self):
        data = self.lastAtCmdRx.decode('UTF-8')
        return data

    # sends a command via serial port
    def sendMessage(self, msg):
        msg = '{}\r\n'.format(msg)
        self.sendCmdAt(msg)
        self.getAtAnswer()
    
    def sendPacketToGateway(self, message):
        cmd = 'AT+SEND=' + str(message)
        self.sendMessage(cmd)
        # self.printLstAnswer() #DEBUG

    def sendJoinRequest(self):
        self.sendMessage('AT+JOIN')
        # self.printLstAnswer() #DEBUG

    def checkJoinStatus(self):
        self.sendMessage('AT+NJS?')
        # self.printLstAnswer() #DEBUG
        answer_data = self.getLstAnswer()
        data = returnFilteredINTs(answer_data)
        try:
            status = data[0]
            if status == 0:
                return False
            elif status == 1:
                return True
        except:
            print("[ERROR] Error aquiring join status! Please, check the serial connection")
            killScript()
            return None

    # returns the last measured RSSI
    def getUpdatedRSSI(self):
        self.resetSerialPort()
        self.sendMessage('AT+RSSI')
        answer = self.getLstAnswer()
        answerData = map(int, re.findall('-?\d+', answer)) # uses regex to filter the output
        RSSIFullData = list(answerData) # last, min, max, avg (NOTE: since last device reset/reboot)
        # print("answer:", answer) #DEBUG
        # print("answerData:", answerData) #DEBUG
        # print("RSSIFullData", RSSIFullData) #DEBUG
        lastPktRSSI = RSSIFullData[0]
        
        # print("lastPktRSSI:", lastPktRSSI) #DEBUG

        return lastPktRSSI

# Helper functionality / Utilities #
# Safely ends the script
def killScript():
    if endDevice != None:
        endDevice.closeSerialPort()
    raise SystemExit(0) # stops the exectution

# Creates the CSV file and adds the header to it
def prepare_CSV_file_save(heading):
    current_date_time = datetime.now()
    date_time = str(f"{current_date_time.year}-{current_date_time.month}-{current_date_time.day}_{current_date_time.hour}-{current_date_time.minute}-{current_date_time.second}")
    file_name = date_time + "_LoRa-Deice-GPS-RSSI-data.csv"

    write_CSV_content(file_name, heading)
    print("[INFO] Writing data to the file", file_name)
    return file_name

def write_CSV_content(file_name, content):
    with open(file_name, 'a+') as f: #opens in append mode, creates if not exist
        write = csv.writer(f)
        write.writerow(content)
        #TODO Write inside the logs folder

def write_TXT_content(file_name, content):
    with open(file_name, 'w') as output:
        output.write(content)

def open_serial_port():
    try:
        endDevice.openSerialPort()
    except serial.serialutil.SerialException:
        traceback.print_exc() # prints the error stack trace
        print("[ERROR] Error connecting to the serial port!")
        print(f"[INFO] Please check the serial port permissions using ls.\n[INFO] You can also try to run the command below:\nsudo chmod 666 {endDevice.loraSerial.port}\n[INFO] To change the permission")
        killScript()

def returnFilteredINTs(data_stream):
    data_stream_list = data_stream.splitlines()
    # print(data_stream_list) #DEBUG
    filtered_data = []
    for elem in data_stream_list: #ignores anything but int numbers
        try:
            filtered_data.append(int(elem))
        except ValueError:
            pass
    return filtered_data

def main_menu():
    print("\n- Script Main Menu -\n")
    option = print_menu_options() #asks for user input
    
    if option == 0:
        print("[INFO] User asked to exit... Bye!")
        killScript()
    
    elif option == 1:
        endDevice.sendJoinRequest()
        print("[INFO] Request sent, waiting the answer for some seconds... ")
        time.sleep(2)
    
    elif option == 2:
        joinned_network = endDevice.checkJoinStatus()
        if joinned_network == False:
            print("[INFO] Device DIDN'T join the network yet!")
        else:
            print("[INFO] Device already joinned the network")
    
    elif option == 3:
        joinned_network = endDevice.checkJoinStatus() #checks if the device is connected to any network before sending packets
        if joinned_network == False:
            print("[ERROR] Device DIDN'T join any network yet!")
            main_menu()
        else:
            print("How many packets to send?")
            num_pkts = input("\n# pkts: ")
            send_control_packets(int(num_pkts))
    
    else:
        print("[ERROR] An invalid option was choosen, please try again")
    
    main_menu()

def print_menu_options():
    print("Please, choose an option:")
    print("\
1- Send a join request\n\
2- Get the join status\n\
3- Start sending the control packets\n\
0- Exit the program")
    opt = input("\nYour option: ")
    return int(opt)

# Calls the TTN Storage API via Curl-like command
def call_storage_API(num_packets, app_name, key, q_type, file_name):
    #NOTE: Adapt the URL below according to your neeeds
    #Reference: https://www.thethingsindustries.com/docs/integrations/storage/retrieve/

    clean_file_name = file_name.split('_') #splits the filename in parts
    api_file_name = clean_file_name[0] + '_' + clean_file_name[1] + "_Storage-API-data.txt" #gets only date + time and adds the name
    
    headers = {
        'Authorization': f'Bearer {key}',
        'Accept': 'text/event-stream',
    }

    api_response = requests.get(f'https://nam1.cloud.thethings.network/api/v3/as/applications/{app_name}/packages/storage/{q_type}?limit={num_packets}', headers=headers)

    print(f"[INFO] Done downloading API data\n[INFO] Saving to the file {api_file_name}")
    write_TXT_content(api_file_name, api_response)

# Helper to configure the API parameters or to skip calling it
def storage_API_menu(packets_sent, file_name):
    api_application_name = "teste-ufjf"
    api_query_type = "uplink_message"

    print("Do you want to try to connect to the TTN Storage API?\nNOTE: an active internet connection is required")
    continue_to_call_api = str(input("\nAnswer ([y]es/[n]o): "))

    if continue_to_call_api == 'n' or continue_to_call_api == 'no':
        print("[INFO] Skipped connecting to the Storage API")
    elif continue_to_call_api == 'y' or continue_to_call_api == 'yes':
        print(f"How many packets do you want to get?\nNOTE: It will get the last N packets (i.e. The N more recent packets received by TTN NS)\nSuggestion: {packets_sent}")
        num_packets_to_get = int(input("\nAnswer (integer): "))
        print(f"[INFO] Quering the application {api_application_name} for the last {num_packets_to_get} of data type {api_query_type}\nYou must provide your API key now, please.")
        api_key = str(input("Paste it here: "))

        call_storage_API(num_packets_to_get, api_application_name, api_key, api_query_type, file_name)
    else:
        print("[ERROR] Invalid answer, please type 'y' or 'n'")
        storage_API_menu(packets_sent, file_name)

def send_control_packets(num_packets_to_send):
    # Vars / Pre setup #
    delayBetweenPkt_sec = 2*60 #NOTE: Delay that adheres to EU's 1% maximum duty cycle on SF12. Use 15*60 for 0.1%. Source: https://github.com/kephas/lora-calculator
    data_to_store_header = ["Time", "Packet #", "Latitude", "Longitude", "Altitude", "GPS Precision", "# Satellites", "ED RSSI"]
    HOST = 'localhost'  # The server's hostname or IP address (to get  the GPS position from)
    PORT = 20175        # The port used by the server

    # open up a socket to communicate with the GPS device
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"[INFO] Successfully connected to {HOST}:{PORT}")
        except ConnectionRefusedError:
            print(f"[ERROR] Got \"connection refused\" error while trying to connect to {HOST}:{PORT}")
            print("[INFO] Make sure you have properly setup the GPS device\n[INFO] Remember to make the port redirect. You can use the command below\nadb forward tcp:20175 tcp:50000\n[INFO] To enable it")
            killScript()

        id = 0 #packet counter
        file_name = prepare_CSV_file_save(data_to_store_header) #creates a new CSV file and returns the file name

        print(f"Sending {num_packets_to_send} control packets...")
        while id < num_packets_to_send:
            try:
                now = datetime.now()
                time_hour = now.strftime("%H:%M:%S")
                data = s.recv(1024).decode("utf-8") #reads 1024 bytes from the buffer and converts it to utf-8 chars
                full_GPS_data = data.splitlines(0) #splits the data in a list of strings
                # print(f"full_GPS_data: {full_GPS_data}") #DEBUG

                pos_pattern = ".GPGGA*" #regex pattern to find the GPGGA GPS data
                filtered_GPS_data = [x for x in full_GPS_data if re.match(pos_pattern, x)] #matches the pos_pattern pattern using list comprehension
                # print(f"filtered_GPS_data: {filtered_GPS_data}") #DEBUG
                position = filtered_GPS_data[0] #gets the first match

                #parses the data retrieved from the phone
                latitude = pynmea2.parse(position).latitude #latitude using float type (unit: decimal degrees)
                longitude = pynmea2.parse(position).longitude #longitude using float type (unit: decimal degrees)
                altitude = pynmea2.parse(position).altitude #altitude in meters, above sea level
                precision = pynmea2.parse(position).gps_qual #quality of GPS reception (should be = '1')
                satellites = pynmea2.parse(position).num_sats #number of connected satellites (the higher, the better)

                endDevice.sendPacketToGateway(id) #sends a packet containing the id inside
                time.sleep(2)
                lastRSSI = endDevice.getUpdatedRSSI() #RSSI measured by the device

                data_to_send = '[{}] Id:{}, Lat: {}, Lon: {}, Alt:{}, Qual:{}, Sats:{}, RSSI:{}'. \
                format(time_hour, id, latitude, longitude, altitude, precision, satellites, lastRSSI)

                print(data_to_send)

                data_to_store = [time_hour, id, latitude, longitude, altitude, precision, satellites, lastRSSI]
                write_CSV_content(file_name, data_to_store)
            
                id = id+1 #increments the couter

                print(f"[INFO] Packet {id} sent, sleeping...")
                time.sleep(5)
                # time.sleep(delayBetweenPkt_sec)

            except IndexError:
                s.close()
                traceback.print_exc() # prints the error stack trace
                print("\n[ERROR] Failed to get the GPS data\n[INFO] Please check the USB connection to the phone")
                killScript()

            except serial.serialutil.PortNotOpenError:
                print("[INFO] Opening the serial connection again...")
                open_serial_port()
                print("[INFO] Serial port connection successfully reconnected")
            
            except KeyboardInterrupt:
                s.close() #closes the connection to the GPS server
                print("\n[INFO] User asked to exit... Bye!")
                killScript()

    s.close() #closes the connection to the GPS server
    endDevice.closeSerialPort() #TODO Try to remove that line and test if serial.serialutil.PortNotOpenError exception stops to occur

    storage_API_menu(num_packets_to_send, file_name) #calls the API

# Global Vars #
endDevice = LoraEndDevice() # instantiate the ED object

def main():
    #NOTE If rssi still fails, try using AT+NLC (see manual)
    #TODO save output files in folders to avoid clutter

    open_serial_port() #tries to connect to the device

    main_menu() #calls the program's main menu

# Calls the main function
if __name__ == "__main__":
    main()
