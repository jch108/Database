import unittest
import database
import os, random, json, time, atexit
from PIL import Image

class TestPlantDatabase(unittest.TestCase):
    def testEmptyInput(self):
        plants = []
        temp, humid, ec, ph = database.getPlantData(plants)

        self.assertIsNone(temp)
        self.assertIsNone(humid)
        self.assertIsNone(ec)
        self.assertIsNone(ph)

    def testInvalidPlant(self):
        plants = ["plant"]
        temp, humid, ec, ph = database.getPlantData(plants)

        self.assertIsNone(temp)
        self.assertIsNone(humid)
        self.assertIsNone(ec)
        self.assertIsNone(ph)
    
    def testOnePlant(self):
        plants = ["ocimum basilicum"]
        temp, humid, ec, ph = database.getPlantData(plants)

        print("temp: ", temp)
        print("humid: ", humid)
        print("EC: ", ec)
        print("Ph: ", ph)


        self.assertEqual(temp, 20)
        self.assertEqual(humid, 55)
        self.assertEqual(ec, 1175)
        self.assertEqual(ph, 7.0)

    def testTwoPlants(self):
        plants = ["white zantedeschia aethiopica", "adansonia digitata"]
        temp, humid, ec, ph = database.getPlantData(plants)
        
        print("-------------")
        print("temp: ", temp)
        print("humid: ", humid)
        print("EC: ", ec)
        print("Ph: ", ph)

        self.assertEqual(temp, 20)
        self.assertEqual(humid, 56)
        self.assertEqual(ec, 1118)
        self.assertEqual(ph, 7.0)

    def testRandomPlants(self):
        json_files = [f for f in os.listdir('json') if f.endswith(".json")]
        plants = random.sample([os.path.splitext(f)[0] for f in json_files], random.randint(1, 3))
        temp, humid, ec, ph = database.getPlantData(plants)

        for plant_id in plants:
            with self.subTest(plant_id=plant_id):
                with open(f'json/{plant_id}.json', "r") as json_file:
                    plant_data = json.load(json_file)
                    parameter_data = plant_data.get("parameter")

                    max_ec = parameter_data.get("max_soil_ec")
                    min_ec = parameter_data.get("min_soil_ec")
                    self.assertTrue(min_ec <= ec)
                    max_temp = parameter_data.get("max_temp")
                    min_temp = parameter_data.get("min_temp")
                    self.assertTrue(min_temp <= temp <= max_temp)
                    max_humidity = parameter_data.get("max_env_humid")
                    min_humidity = parameter_data.get("min_env_humid")
                    self.assertTrue(min_humidity <= humid <= max_humidity)

    def testPerformance(self):
        start_time = time.time()

        json_files = [f for f in os.listdir('json') if f.endswith(".json")]
        plants = random.sample([os.path.splitext(f)[0] for f in json_files], 25)
        temp, humid, ec, ph = database.getPlantData(plants)

        end_time = time.time()

        time_taken = end_time - start_time

        self.assertLessEqual(time_taken, 0.5)

    def testCvDatabse(self):
        with open ('download.jpg', 'rb') as file:
            binaryData = file.read()
        # Test data
        timestamp = '11_6_14'
        raw_image_data = binaryData
        threshold_image_data = binaryData
        Roi_image_data = binaryData
        plant_data = ['Plant1', 'Plant2', 'Plant3']
        days_identified = [10, 15, 20]
        days_harvest = [30, 35, 40]
        replace_flags = [0, 1, 0]
        harvest_flags = [1, 0, 0]
        area = [1000, 30.0, 28.2]
        grow_rate = [2.0, 1.5, 1.8]

        # Insert data into the database
        database.insertCvData(
            timestamp,
            raw_image_data,
            threshold_image_data,
            Roi_image_data,
            plant_data,
            days_identified,
            days_harvest,
            harvest_flags,
            replace_flags,
            area,
            grow_rate
        )

        # Retrieve data from the database
        retrieved_data = database.getCvData(timestamp)

        # Check if data was successfully retrieved
        self.assertIsNotNone(retrieved_data, f"No data found for timestamp {timestamp}")

        # Compare the retrieved data with the expected data
        self.assertEqual(retrieved_data['timestamp'], timestamp)
        self.assertEqual(retrieved_data['raw_image'], raw_image_data)
        self.assertEqual(retrieved_data['threshold_image'], threshold_image_data)
        self.assertEqual(retrieved_data['Roi_image'], Roi_image_data)


if __name__ == '__main__':
    database.setupCvDatabase()

    unittest.main()
    database.closeSerial()
    # database.clear_database()
    
def cleanup():
    # Place your cleanup tasks here
    print("Program is exiting. Performing cleanup...")
    database.closeDatabase()
    database.clearCvDatabase()

# Register the cleanup function to be called when the program exits
atexit.register(cleanup)