import communications
import csv
import fileHandling
import serial
from time import sleep
from time import time
from plotting import remove_every_nth
import pygaps as pg
import pygaps.modelling as pgm
import pandas as pd
import matplotlib.pyplot as plt
import pygaps.graphing as pgg
from math import log10

""" Groups of functions used when alkalinity mode is active in BaPvu """

def which_electrolyzer():
    """  Reads a config file which has the electrolyzer channel number written on line one """




    return

def which_sensors():
    """  Reads a config file which has the sensor channel number written on line 2 for first eDAQ, line 3 for second eDAQ....etc 
    configuration should be in order of com value. Ex. COM3 will come before COM4 in the file...etc.
     """
    


    return


def fit_to_langmuir(file='calibration_data.csv', adsorbate='H+', sensor_material='SWCNT', temp=298):
    """ Takes a file path for calibration data 
    Returns a three site langmuir isotherm fit.
    If it fails to fit to three site langmuir, it will try to guess the model to use for fitting.
    pygaps documentation: https://pygaps.readthedocs.io/en/master/examples/modelling.html
    """

    df = pd.read_csv(file)
    log_concentration = df['pH'].to_list()
    concentration = [10**((-1)*pH) for pH in log_concentration] # convert to molar
    sensor_current = df['sensor_current'].to_list()
    
    try:
        model = pg.ModelIsotherm(
            material=sensor_material,
            adsorbate=adsorbate,
            temperature=298,
            pressure=concentration,
            loading=sensor_current,
            model='TSLangmuir',
            #optimization_params=dict(max_nfev=1e7),
            verbose=True
            )

    except Exception as e:
        print(e)


    #ax = pgg.plot_iso(
    # model,
    # branch = 'all',
    # color=False
    # )
    # #plt.show()
    return model

def convert_curent_to_pH(sensor_current, isotherm):
    """ Takes in sensor current and converts to pH. Uses langmuir fit of sensor response for a given pH calibration """

    pH = log10(isotherm.pressure_at(loading=sensor_current))*(-1) # to interpolate pH

    return pH


def set_electrolyzer_potential(serial_obj, potential, channel):
    """ Potential in milivolt 
    Note: setting potential will end data acquision.
    Returns electrolyzer potential.
    """

    # beep to indicate that potential has been set 
    communications.write_data(serial_obj, 'beep')

    command = 'set channel {} Vex {}'.format(channel,potential)
    communications.write_data(serial_obj, command)

    response = []

    while len(response) != 5: # wait for respones of correct len
        response = communications.read_data(serial_obj) # returns list.
        #Ex. ['Channel' '1', 'Vex', '10.0', 'mV']

    new_potential = float(response[3])

    return new_potential

def get_channel_current(serial_obj, channel):

    command = 'r'
    communications.write_data(serial_obj, command)

    response = []

    while len(response) != 5: # wait for respones of correct len
        response = communications.read_data(serial_obj) # returns list.
        #Ex. ['Channel' '1', 'Vex', '10.0', 'mV']


    response_cleaned = remove_every_nth(response,2,skip_first_element=False) # removes units
    
    current = response_cleaned[channel-1]


    return current


def autorange_current(serial_obj, old_range, channel, current_voltage, next_voltage):

    available_ranges = [20, 200, 2000, 20000, 200000, 2000000] # nA
    # documentation: https://www.edaq.com/wiki/EPU452_Manual

    # get current for channel.
    current = get_channel_current(serial_obj, channel)

    # get potential 
    # use ohm's law to calculate resistance
    resistance = current_voltage/current
    predicted_next_current = next_voltage/resistance
    # make adjust range if next voltage is over 85% of max of range.
    
    if predicted_next_current > 0.85*old_range:
        new_range = next(x for x in available_ranges if x > predicted_next_current)
        # find to next value within that range.

    command = 'set channel {} range {}'.format(channel,new_range)
    communications.write_data(serial_obj, command)
    
    return new_range



def convert_electrolyzer_current_to_alkalinity():


    return



def storeData():
    """ Will write the alkalinity data in a separate file from the raw data 
    key parameters: 
    - pH according to each sensor.

    """

    return

def compare_pH():
    """ Compares current pH reading to last reading in file 
    Returns true if pH is same (within tolerance)
    Returns flase if pH is different (within tolerance)
    Returns None type if file is empty
    """


    return


def voltage_sweep(filepath, fieldnames, electrolyzer_channel, min_voltage, max_voltage, volt_step_size, volt_limit, time_per_step, daq_num):
    """ Sweeps electrolyzer voltage and records voltage, current and time in a separate file
    This data can be combined with sensing data to examine the relationship between electrolyzer current/voltage and pH.
    The pH can be calibrated separately.
    Time_per_step in seconds.
    """
    daq_num=1
    dev_channel_num = 4
    data_expected_per_channel = 2 # number or 'off' and a unit.
    data_len_per_device = dev_channel_num*data_expected_per_channel
    expected_rowsize = data_len_per_device*daq_num

    datapoints_per_potential = 1*time_per_step # since each step is 1 second


    new_filepath = filepath+"_sweep.csv" ### change filename to include sweep
    new_fieldnames = fieldnames # creating a local copy of fieldnames
    new_fieldnames.append('electrolyzer_potential')
    new_fieldnames.append('unit')
    #### New fields: systime, ch1, ch2, ch3, ch4...etc., electrolyzer_potential
    fileHandling.filecreate(new_filepath, new_fieldnames)

     # Reading a list of com ports
    ports = communications.get_com_ports()

    if len(ports) > 3:
        
        print("Reading more than 3 eDAQ's is currently unsuported!")

        return
    
    if max_voltage > volt_limit:

        print("Error: given voltage range exceeds device limit.")

        return
    
    #creating a list of serial objects.
    ser = [
            serial.Serial(
            port = port,
            timeout=None, #Waits indefinitely for data to be returned.
            baudrate = 115200,
            bytesize=8,
            parity='N',
            stopbits=1
            )

            for port in ports
    ]


    buffer = [] # save buffer as dictionary. All data is written to the file once the sweep is completed.
    
    for serial_obj in ser:
        electrolyzer_setpoint = set_electrolyzer_potential(serial_obj, min_voltage, electrolyzer_channel)
    
    while electrolyzer_setpoint <= max_voltage:

        for serial_obj in ser:
            electrolyzer_setpoint = set_electrolyzer_potential(serial_obj, potential=(electrolyzer_setpoint), channel=electrolyzer_channel)
            communications.write_data(serial_obj, 'i 1')
        
        counter = 0 # counts the number of lines appended to dictionary
        
        while counter != datapoints_per_potential:
            
            sleep(1)
            data = []
            
            for serial_obj in ser:
                new_data = communications.read_data(serial_obj)
                data.extend(new_data)
                
            if len(data) != expected_rowsize:
                print('Warning: Unexpected row size. Row discarded.')
                continue

            time_received = time()
            data.insert(0, str(time_received))
            data.extend([str(electrolyzer_setpoint),'mV'])

            buffer.append(data)

            counter = counter + 1

            if len(buffer) == datapoints_per_potential: # write to file before each potential increment.
                communications.write_to_file(buffer,new_filepath)
                buffer = [] # clears buffer
            else:
                continue
        
        electrolyzer_setpoint = electrolyzer_setpoint+volt_step_size

    for serial_obj in ser:
        serial_obj.close()
    
    print("Sweep complete.")

    return


def alkalinity_test():

    electrolyzer_channel = which_electrolyzer()
    sensor_channels = which_sensors()

    """
    Read values using communication library.
    Take entire chunk.
    Chunksize can be set in alkalinity mode.
    take mean for each channel for a given chunk.
    return this mean as 'data'
    """
    
    data = None

    new_pH = convert_curent_to_pH(data, sensor_channels) # returns a list of pH's for all three sensors on each eDAQ

    if compare_pH(file, new_pH, tolerance) is True:

        storeData()

    elif compare_pH(file, new_pH, tolerance) is False:
        
        while compare_pH(file, new_pH, tolerance) is False:

            set_electrolyzer_potential()

            sleep(time_delay) # should be a delay based on the size of the channel.

        # recalculate alkalinity


    else: ## if None type is returned due to empty file

        storeData()


    return 0 # if successfully completed. Set to return 1 if error since it shouldn't block the main process if it fails for some reason.
