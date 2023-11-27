import os
import json
import sqlite3
from statistics import mean, median
import random
import serial
import time
import threading
import io
# from flask import Flask, request, jsonify, render_template

#-----------------------------------------------------------------------
#----------------------------------DBMS---------------------------------
#-----------------------------------------------------------------------

#connect to databse
conn = sqlite3.connect('plant_database.db')
cursor = conn.cursor()

conn2 = sqlite3.connect('cvInfo.db')
cursor2 = conn2.cursor()

#initialize table
cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS plants (
        pid TEXT PRIMARY KEY,
        basic JSON,
        display_pid TEXT,
        maintenance JSON,
        parameter JSON,
        image TEXT
    )
''')

def loadDatabase():
    #populate database
    for file_name in os.listdir('json'):
        if file_name.endswith(".json"):
            file_path = os.path.join('json', file_name)

            #read and parse the JSON data from the file
            try:
                with open(file_path, "r") as json_file:
                    plant_data = json.load(json_file)

                #check if plant_data is not None before extracting the plant ID (pid)
                if plant_data is not None and "pid" in plant_data:
                    pid = plant_data["pid"]
                    basic_data = json.dumps(plant_data.get("basic"))
                    display_pid = plant_data.get("display_pid")
                    maintenance_data = json.dumps(plant_data.get("maintenance"))
                    parameter_data = json.dumps(plant_data.get("parameter"))
                    image = plant_data.get("image")

                    #insert the data into the "plants" table
                    cursor.execute(
                        "INSERT OR REPLACE INTO plants (pid, basic, display_pid, maintenance, parameter, image) VALUES (?, ?, ?, ?, ?, ?)",
                        (pid, basic_data, display_pid, maintenance_data, parameter_data, image)
                    )
                    #commit the changes to the database
                    conn.commit()

                else:
                    print(f"Warning: Missing or invalid 'pid' in JSON file - {file_name}")
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON file - {file_name}: {str(e)}")

def setupCvDatabase():
    cursor2.execute('''
        CREATE TABLE IF NOT EXISTS cvInfo (
            id INTEGER PRIMARY KEY,
            timestamp TEXT UNIQUE,
            raw_image BLOB,
            threshold_image BLOB,
            Roi_image BLOB,
            plant_1 TEXT,
            plant_2 TEXT,
            plant_3 TEXT,
            Days_identified1 INTEGER,
            Days_identified2 INTEGER,
            Days_identified3 INTEGER,
            Days_Harvest1 INTEGER,
            Days_Harvest2 INTEGER,
            Days_Harvest3 INTEGER,
            Harvest_Flag1 INTEGER,
            Harvest_Flag2 INTEGER,        
            Harvest_Flag3 INTEGER,
            Replace_Flag1 INTEGER,
            Replace_Flag2 INTEGER,
            Replace_Flag3 INTEGER,
            Area_1 REAL,
            Area_2 REAL,
            Area_3 REAL,
            Grow_Rate1 REAL,
            Grow_Rate2 REAL,
            Grow_Rate3 REAL
        )
    ''')
    conn2.commit()

#-----------------------------------------------------------------------
#---------------------Database Operations-------------------------------
#-----------------------------------------------------------------------

def calculateTemp(temperature_values):
    median_temperature = median(temperature_values)

    #set lower and upper temperature limits
    if(median_temperature < 16):
        median_temperature = 16
    if(median_temperature > 40):
        median_temperature = 40

    return round(median_temperature)

def calculateHumidity(humidity_values):
    median_humidity = median(humidity_values)

    #set lower and upper humidity limits
    if(median_humidity < 25):
        median_humidity = 25
    if(median_humidity > 95):
        median_humidity = 95

    return round(median_humidity)

def calculateEC(ec_values):
    mean_ec = mean(ec_values)

    return round(mean_ec)

def calculatePH(ph_values):
    mean_ph = mean(ph_values)
    
    #round the pH to the nearest 0.5
    mean_ph = round(mean_ph * 2) / 2

    return mean_ph

def getPlantData(plant_ids):

    if(plant_ids == []):
        return None, None, None, None
    temperature_values = []
    humidity_values = []
    ec_values = []
    ph_values = []

    for plant_id in plant_ids:
        try:
            #get JSON data of plant from database
            cursor.execute("SELECT parameter FROM plants WHERE pid = ?", (plant_id,))
            plant_parameter = cursor.fetchone()

            if plant_parameter:
                parameter_data = json.loads(plant_parameter[0])

                max_temp = parameter_data.get("max_temp", 0)
                min_temp = parameter_data.get("min_temp", 0)
                max_humidity = parameter_data.get("max_env_humid", 0)
                min_humidity = parameter_data.get("min_env_humid", 0)
                max_ec = parameter_data.get("max_soil_ec", 0)
                min_ec = parameter_data.get("min_soil_ec", 0)

                #calculate midpoint for each parameter
                temperature = (max_temp + min_temp) / 2.0
                humidity = (max_humidity + min_humidity) / 2.0
                soil_ec = (max_ec + min_ec) / 2.0

                ph = parameter_data.get("ideal_ph", 0)

                temperature_values.append(temperature)
                humidity_values.append(humidity)
                ec_values.append(soil_ec)
                ph_values.append(ph)
            else:
                print(f"Plant with ID '{plant_id}' not found in the database")
                return None, None, None, None

        except Exception as e:
            print(f"Error querying the database for plant '{plant_id}': {str(e)}")

    temp = calculateTemp(temperature_values)
    humid = calculateHumidity(humidity_values)
    ec = calculateEC(ec_values)
    ph = calculatePH(ph_values)
    return temp, humid, ec, ph

def closeDatabase():
    conn.close()

#-----------------------------------------------------------------------
#---------------------Computer Vision Communication---------------------
#-----------------------------------------------------------------------

def insertCvData(timestamp, raw_image, threshold_image, Roi_image, plant_data, days_identified, days_harvest, harvest_flags, replace_flags, area, grow_rate):

    try:
        cursor2.execute('''
            INSERT INTO cvInfo (
                timestamp,
                raw_image,
                threshold_image,
                Roi_image,
                plant_1,
                plant_2,
                plant_3,
                Days_identified1,
                Days_identified2,
                Days_identified3,
                Days_Harvest1,
                Days_Harvest2,
                Days_Harvest3,
                Harvest_Flag1,        
                Harvest_Flag2,  
                Harvest_Flag3,  
                Replace_Flag1,
                Replace_Flag2,
                Replace_Flag3,
                Area_1,
                Area_2,
                Area_3,
                Grow_Rate1,
                Grow_Rate2,
                Grow_Rate3
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, raw_image, threshold_image, Roi_image,
              plant_data[0], plant_data[1], plant_data[2],
              days_identified[0], days_identified[1], days_identified[2],
              days_harvest[0], days_harvest[1], days_harvest[2],
              harvest_flags[0], harvest_flags[2], harvest_flags[2],
              replace_flags[0], replace_flags[1], replace_flags[2],
              area[0], area[1], area[2],
              grow_rate[0], grow_rate[1], grow_rate[2]))

        conn2.commit()
    except sqlite3.IntegrityError:
        print(f"Data for timestamp {timestamp} already exists.")
    
def getCvData(timestamp):
    cursor2.execute('''
        SELECT * FROM cvInfo
        WHERE timestamp = ?
    ''', (timestamp,))
    
    data = cursor2.fetchone()

    if data:
        columns = [desc[0] for desc in cursor2.description]
        data_dict = dict(zip(columns, data))
        return data_dict
    else:
        return None

def clearCvDatabase():
    # cursor2.execute('DROP TABLE IF EXISTS cvInfo')
    # conn2.commit()
    conn2.close()

#-----------------------------------------------------------------------
#---------------------Control System Communication----------------------
#-----------------------------------------------------------------------

# ser = serial.Serial('COM1', 9600)

# Mock serial connection
fake_serial = io.BytesIO()
ser = fake_serial

light_cmd = 0

def sendDataToAtMega(temp, humid, ec, ph):
    global ser
    # Send data to AtMega microcontroller
    data = f"T:{temp},H:{humid},EC:{ec},PH:{ph},L:{light_cmd}\n"
    print(data)
    print("Data.enocde: ", data.encode())
    ser.write(data)

def receiveDataFromAtMega():
    try:
        # Read data from the serial port
        raw_data = ser.readline().decode().strip()

        # Parse the received data
        data_parts = raw_data.split(',')
        temp = float(data_parts[0].split(':')[1])
        humid = float(data_parts[1].split(':')[1])
        ec = float(data_parts[2].split(':')[1])
        ph = float(data_parts[3].split(':')[1])

        print(f"Received Data: Temperature={temp}, Humidity={humid}, EC={ec}, pH={ph}")

        return temp, humid, ec, ph

    except Exception as e:
        print(f"Error receiving data from AtMega: {e}")
        return None

def closeSerial():
    ser.close()
    

#COMMENTED OUT TO RUN TESTS
# def lightThread():
#     while True:
#         current_time = time.localtime()
#         current_hour = current_time.tm_hour
#         # 6am to 8pm
#         if 6 <= current_hour < 22:
#             light_cmd = 1;
#         else:
#             light_cmd = 0;

#         # Check every hour
#         time.sleep(3600)

#     #flags for water level etc

# lighting_thread = threading.Thread(target=lightThread)
# lighting_thread.daemon = True
# lighting_thread.start()

#-----------------------------------------------------------------------
#---------------------Website Communication-----------------------------
#-----------------------------------------------------------------------

# from flask import Flask, render_template
# from flask_socketio import SocketIO

# app = Flask(__name__)
# socketio = SocketIO(app)

# # Placeholder data for plant information
# app.config['plants'] = {
#     "plant1": {
#         "name": "Plant 1",
#         "growRate": "Some rate",
#         "areaPercentage": "Some percentage",
#         "daysSinceIdentification": "Some days",
#         "daysUntilHarvest": "Some days",
#     },
#     "plant2": {
#         "name": "Plant 2",
#         "growRate": "Some rate",
#         "areaPercentage": "Some percentage",
#         "daysSinceIdentification": "Some days",
#         "daysUntilHarvest": "Some days",
#     },
#     "plant3": {
#         "name": "Plant 3",
#         "growRate": "Some rate",
#         "areaPercentage": "Some percentage",
#         "daysSinceIdentification": "Some days",
#         "daysUntilHarvest": "Some days",
#     },
#     # Add information for other plants as needed
# }

# # Placeholder data for chamber conditions
# app.config['chamber_conditions'] = {
#     "setpoint_temperature": 25.0,  # Initial setpoint temperature
#     "setpoint_humidity": 60.0,
#     "setpoint_electrical_conductivity": 1.5,
#     "setpoint_ph": 6.0,
#     "actual_temperature": 24.0,
#     "actual_humidity": 58.0,
#     "actual_electrical_conductivity": 1.4,
#     "actual_ph": 5.8,
# }

# @app.context_processor
# def inject_data():
#     return dict(
#         plants=app.config['plants'],
#         chamber_conditions=app.config['chamber_conditions'],
#         setpoint_temperature=app.config['chamber_conditions']["setpoint_temperature"],
#         setpoint_humidity=app.config['chamber_conditions']["setpoint_humidity"],
#         setpoint_electrical_conductivity=app.config['chamber_conditions']["setpoint_electrical_conductivity"],
#         setpoint_ph=app.config['chamber_conditions']["setpoint_ph"],
#         actual_temperature=app.config['chamber_conditions']["actual_temperature"],
#         actual_humidity=app.config['chamber_conditions']["actual_humidity"],
#         actual_electrical_conductivity=app.config['chamber_conditions']["actual_electrical_conductivity"],
#         actual_ph=app.config['chamber_conditions']["actual_ph"],
#         # Plant-specific variables
#         plant1=app.config['plants'].get("plant1", {}),
#         plant2=app.config['plants'].get("plant2", {}),
#         plant3=app.config['plants'].get("plant3", {})
#     )

# @app.route('/')
# def index():
#     return render_template('index.html')


# @app.route('/update_setpoint_temperature')
# def update_setpoint_temperature():
#     # Update the setpoint temperature
#     app.config['chamber_conditions']["setpoint_temperature"] += 1.0
#     socketio.emit('update_temperature', app.config['chamber_conditions']["setpoint_temperature"])
#     print("Setpoint temperature updated successfully.")
#     return "Setpoint temperature updated successfully."

# if __name__ == '__main__':
#     socketio.run(app, debug=True, use_reloader=False)
