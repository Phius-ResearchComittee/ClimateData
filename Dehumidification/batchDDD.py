# Import dependencies

import pandas as pd
import psychrolib
import os
import json
import PySimpleGUI as sg

sg.theme('BrightColors')
layout = [[sg.Text('Study Folder:', size =(25, 1)),sg.InputText('C:/Users/amitc_crl/OneDrive/Documents/GitHub/ClimateData/Dehumidification/IL', key='studyFolder'), sg.FolderBrowse()],      
          [sg.Button('Calculate'), sg.Exit()]]      

window = sg.Window('Dehumidification Degree Day Calculator v23.1.1', layout)      

while True:                             # The Event Loop
    event, values = window.read() 
    if event == 'Calculate':
        studyFolder =  str(values['studyFolder']) #'C:/Users/amitc_crl/OneDrive/Documents/GitHub/ClimateData/Dehumidification/IL'
    

        os.chdir(str(studyFolder))
        psychrolib.SetUnitSystem(psychrolib.IP)

        if os.path.exists('out.csv'):
            os.remove('out.csv')

        files = os.listdir()
        locations = []
        dehumDegreeDays = []

        for file in files:
            weatherFile = str(file)

            data = pd.read_excel(str(weatherFile))
            location = data['Passive House Planning'].values[4]
            altitude = data['Unnamed: 7'].values[19]
            # altitude = 0
            atmPressure = psychrolib.GetStandardAtmPressure(altitude)
            humRatioLimit = 0.01

            days = []
            dewPoints = []
            humRatios = []
            deltas = []
            ddds = []

            for x in range(12):
                n = x + 2
                column = 'Unnamed: ' + str(n)
                day = data[str(column)].values[3]
                dewPoint = data[str(column)].values[26]
                days.append(day)
                dewPoints.append(dewPoint)

            for x in dewPoints:
                humRatio = psychrolib.GetHumRatioFromTDewPoint(x,atmPressure)
                humRatios.append(humRatio)
                delta = humRatio - humRatioLimit
                if delta > 0:
                    deltas.append(delta)
                else:
                    deltas.append(0)

            for x in range(len(days)):
                ddd = days[x] * deltas[x]
                ddds.append(ddd)

            ddd = sum(ddds)

            locations.append(location)
            dehumDegreeDays.append(ddd)

        df  = pd.DataFrame(locations,dehumDegreeDays)

        # df  = pd.DataFrame({'Locations':locations},{'DDD':dehumDegreeDays})


        df.to_csv('out.csv')
        sg.popup('Done! Go check out.csv')


    if event == sg.WIN_CLOSED or event == 'Exit':
        break      

window.close()




