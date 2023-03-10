#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 10 11:42:26 2023

@author: Pedro Corral
"""

import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

SOUTH = 1
NORTH = 0

NCARS = 100
NPED = 10
TIME_CARS = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRGIAN = (30, 10) # normal 1s, 0.5s

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.patata = Value('i', 0)
        
        self.ncarsN = Value('i', 0)
        self.ncarsS = Value('i', 0)
        self.nPed   = Value('i', 0)
        
        self.canPassCN = Condition(self.mutex)
        self.canPassCS = Condition(self.mutex)
        self.canPassP  = Condition(self.mutex)
        
        self.ncNwaiting = Value('i', 0)
        self.ncSwaiting = Value('i', 0)
        self.nPwaiting  = Value('i', 0)
        
        self.waitCN    = Condition(self.mutex)
        self.waitCS    = Condition(self.mutex)
        self.waitP     = Condition(self.mutex)

    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        if direction==NORTH:
            self.ncNwaiting.value+=1
            self.waitCN.wait_for(self.are_waiting_cars_North)
            self.canPassCN.wait_for(self.can_pass_cars_North)
            self.ncarsN.value+=1
            self.ncNwaiting.value-=1
            if self.ncNwaiting.value<=2:
                self.canPassCS.notify_all()
                self.canPassP.notify_all()
        else:
            self.ncSwaiting.value+=1
            self.waitCS.wait_for(self.are_waiting_cars_South)
            self.canPassCS.wait_for(self.can_pass_cars_South)
            self.ncarsS.value+=1
            self.ncSwaiting.value-=1
            if self.ncSwaiting.value<=2:
                self.canPassCN.notify_all()
                self.canPassP.notify_all()
        self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        self.patata.value += 1
        if direction==NORTH:
            self.ncarsN.value-=1
            if self.ncarsN.value==0:
                self.canPassCS.notify_all()
                self.canPassP.notify_all()
        else:
            self.ncarsS.value-=1
            if self.ncarsS.value==0:
                self.canPassCN.notify_all()
                self.canPassP.notify_all()
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        self.nPwaiting.value+=1
        self.waitP.wait_for(self.are_waiting_Pedestrians)
        self.canPassP.wait_for(self.can_pass_Ped)
        self.nPed.value+=1
        self.nPwaiting.value-=1
        if self.nPwaiting.value<=1:
            self.waitCN.notify_all()
            self.waitCS.notify_all()
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        self.nPed.value-=1
        if self.nPed.value==0:
            self.canPassCN.notify_all()
            self.canPassCS.notify_all()
        self.mutex.release()
        
    def can_pass_cars_South(self) -> bool:
        return self.ncarsN.value == 0 and self.nPed.value == 0
    
    def can_pass_cars_North(self) -> bool:
        return self.ncarsS.value == 0 and self.nPed.value == 0
    
    def can_pass_Ped(self) -> bool:
        return self.ncarsN.value == 0 and self.ncarsS.value == 0
    
    def are_waiting_cars_North(self) -> bool:
        return self.ncSwaiting.value<=2 and self.nPwaiting.value<=1
    
    def are_waiting_cars_South(self) -> bool:
        return self.ncNwaiting.value<=2 and self.nPwaiting.value<=1

    def are_waiting_Pedestrians(self) -> bool:
        return self.ncNwaiting.value<=2 and self.ncSwaiting.value<=2
    
    def __repr__(self) -> str:
        return f'Monitor: {self.patata.value}'

def delay_car_north(factor = 3) -> None:
    time.sleep(random.random()/factor)

def delay_car_south(factor = 3) -> None:
    time.sleep(random.random()/factor)

def delay_pedestrian(factor = 3) -> None:
    time.sleep(random.random()/factor)

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}",flush=True)
    monitor.wants_enter_car(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}",flush=True)
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}",flush=True)
    monitor.leaves_car(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}",flush=True)

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}",flush=True)
    monitor.wants_enter_pedestrian()
    print(f"pedestrian {pid} enters the bridge. {monitor}",flush=True)
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}",flush=True)
    monitor.leaves_pedestrian()
    print(f"pedestrian {pid} out of the bridge. {monitor}",flush=True)



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()

def gen_cars(monitor) -> Monitor:
    cid = 0
    plst = []
    for _ in range(NCARS):
        direction = NORTH if random.randint(0,1)==1  else SOUTH
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_CARS))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars = Process(target=gen_cars, args=(monitor,))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars.start()
    gped.start()
    gcars.join()
    gped.join()
    print("FIN DE LA EJECUCIÓN",flush=True)

if __name__ == '__main__':
    main()
