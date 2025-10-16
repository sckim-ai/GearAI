from mastapy import masta_property, MeasurementType 
from mastapy.system_model import Design 
import math
import matplotlib.pyplot as plt
import os

name = 'Run_analysis' 
description = '' 
symbol = '' 
measurement = MeasurementType.SHORT_LENGTH 


@masta_property( 
    name, 
    description=description, 
    symbol=symbol, 
    measurement=measurement) 


def TE_check(design: Design) -> float: 
    
    RPM = 2*math.pi/60

    #결과파일 정리용 list
    result_list = []

    # Static Load 정의하기
    torque_list = [150,200,250]
    rpm_list = [3000,4000,5000]

    static_load = design.design_states[0].static_loads[0]
    
    # Torque와 RPM 정의하여 해석 실행 및 결과 정리
    for torque in torque_list:
        # 효율계산 활성화
        for rpm in rpm_list:
            static_load.transmission_efficiency_settings.include_efficiency = True
            static_load.power_loads[0].torque = torque
            static_load.power_loads[0].speed = rpm*RPM
            #print('rpm:', static_load.power_loads[0].speed)

            #Perform system deflection analysis
            static_load.system_deflection.perform_analysis() 
            total_efficiency = static_load.system_deflection.results_for_root_assembly(design.root_assembly).system_deflection.overall_efficiency_results.efficiency
            print(total_efficiency * 100)
            result_list.append([torque,rpm,total_efficiency*100])
    
    start_torque = 50
    end_torque = 450
    torque_step = 50
    torque_list = range(start_torque,end_torque+1,torque_step) #Using the range function, it is iterative and useful for a for loop. 

    um = 1e6
    cylindrical_gear_mesh = design.root_assembly.cylindrical_gear_sets[0].cylindrical_meshes[0]
    te_list = []
    for torque in torque_list:
        print("original torque = ", design.static_loads[0].power_loads[0].torque)
        design.static_loads[0].power_loads[0].torque = torque #Change the Torque
        print(design.static_loads[0].power_loads[0].torque) #Print the modified torque value
        design.static_loads[0].system_deflection.perform_analysis() #Perform system deflection analysis
        print(design.static_loads[0].system_deflection.results_for_cylindrical_gear_mesh(cylindrical_gear_mesh).basic_ltca_results.peak_to_peak_te*um) #pk-to-pk TE
        te_list.append(design.static_loads[0].system_deflection.results_for_cylindrical_gear_mesh(cylindrical_gear_mesh).basic_ltca_results.peak_to_peak_te*um) #Add the result into a list

    # matplotlib error 해결용
    try:
        os.environ['TCL_LIBRARY'] = rf"C:\Python\Python312\tcl\tcl8.6"
    except:
        print('error')
        return
    
    plt.plot(torque_list, te_list)
    plt.show()