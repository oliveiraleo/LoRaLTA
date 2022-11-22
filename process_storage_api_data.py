import json
import csv
import base64

def get_file_binary_data(file_name):
    with open(file_name, "r") as f:
        print("[INFO] Reading the file", file_name)
        data = f.read()
    
    return data

def process_raw_data(data, file_name_to_save):
    d_list = data.splitlines()
    j_list = []
    id_and_rssi_list = []
    for elem in d_list: #filters only the JSON formatted data
        if elem != '':
            j_list.append(elem)

    header = ['id', 'GW rssi'] #header for the CSV file
    clean_file_name = file_name_to_save.split('_')
    file_name = clean_file_name[0] + '_' + clean_file_name[1] + '_LoRa-RSSI-GW-decoded.csv'
    
    with open(file_name, 'w+') as f:
        write = csv.writer(f) #creates a reader object
        write.writerow(header) #writes the reader line at the beggining of the file

        for elem in j_list: #filters the data of interest and writes it to the CSV file
            dct = json.loads(elem)
            rssi = dct['result']['uplink_message']['rx_metadata'][0]['rssi']

            id_base64 = dct['result']['uplink_message']['frm_payload']
            id_b64_encoded = id_base64.encode('ascii')
            id = base64.b64decode(id_b64_encoded).decode('ascii')

            data_line = [str(id), str(rssi)]
            write.writerow(data_line)

        print(f"[INFO] File {file_name} saved successfully")

def menu():
    print("Please, give the name of the TXT file you want to read from")
    file_name = str(input("Type (or paste) it here: "))

    file_data_raw = get_file_binary_data(file_name)
    process_raw_data(file_data_raw, file_name)

def main():
    menu() #TODO add some commets to explain what is happening here

# Calls the main function
if __name__ == "__main__":
    main()