#Import dependencies

import customtkinter as ctk
import subprocess
import sys
import threading
import ctypes
import importlib
import webbrowser
sys.path.append("pystray-0.19.5\\lib\\pystray")
sys.path.append("keyboard-0.13.5\\keyboard-0.13.5")
import pystray
import keyboard
import calendar
import os
import requests
from datetime import datetime
from PIL import Image, ImageDraw

#Create window
root = ctk.CTk()

days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
calendarDays = []
monthSel = None
yearSel = None
backBtn = None
eventListbox = None
ownFolder = os.path.dirname(os.path.abspath(__file__))
activeDayNum = None
noteColors = {
    "Default Dark": "#1f2c3f",
    "Google Blue": "#1d3d5a",
    "Google Green": "#1e4620",
    "Google Yellow": "#5c501a",
    "Google Red": "#5c1e1e",
    "IMPORTANT":"#9500ff"
}
eventsFile = os.path.join(ownFolder, "events.txt")

if not os.path.exists(eventsFile):
    with open(eventsFile, "w") as f:
        pass

currentYear = datetime.now().year
currentMonthNum = datetime.now().month
currentMonth = months[currentMonthNum - 1]
today = datetime.now().day
thisHour = datetime.now().hour
thisMinute = datetime.now().minute
yearRange = [str(y) for y in range(currentYear - 5, currentYear + 6)]

GithubToken = ""
GistID = ""
syncConfigured = True

configFile = os.path.join(ownFolder, "config.txt")
logFile = os.path.join(ownFolder, "sync.log")

if os.path.exists(configFile):
    with open(configFile, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if val == "paste_github_token_here" or val == "paste_the_id_of_the_gist_you_want_to_sync_to_here" or val is None:
                syncConfigured = False
            else:
                if key == "GithubToken":
                    GithubToken = val
                elif key == "GistID":
                    GistID = val

#Make sure the window looks nice and not awful, like ratshit awful
trans = "#000001"
root.config(bg=trans)
root._fg_color = trans

ctk.set_appearance_mode("Dark")

trayIcon = None

def syncGist():
    if not syncConfigured:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(logFile, "a") as f:
            f.write(f"[{now}] [ERR]: Github Sync Error! Is config.txt properly formatted?\n")
        return

    if not os.path.exists(eventsFile):
        return

    with open(eventsFile, "r") as file:
        passengers = file.read()

    url = f"https://api.github.com/gists/{GistID}"
    headers = {
        "Authorization": f"token {GithubToken}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "files": {
            "events.txt": {
                "content": passengers
            }
        }
    }
    
    def runNetResponse():
        try:
            response = requests.patch(url, json=payload, headers=headers)
            if response.status_code == 200:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(logFile, "a") as f:
                    f.write(f"[{now}] [INF]: Github Sync Successful!\n")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(logFile, "a") as f:
                    f.write(f"[{now}] [ERR]: Oops! We got an error!\n")
                    f.write(f"[{now}] [ERR]: {url} returned error {response.status_code}!\n")
                    f.write(f"[{now}] [ERR]: {response.text}\n")
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(logFile, "a") as f:
                f.write(f"[{now}] [ERR]: Oops! Can't connect to {url}!\n")
                f.write(f"[{now}] [ERR]: Reason: {e}\n")
    threading.Thread(target=runNetResponse, daemon=True).start()
    root.after(0, lambda: dateChange(None))

def downloadGist():
    if not syncConfigured:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(logFile, "a") as f:
            f.write(f"[{now}] [ERR]: Github Sync Error! Is config.txt properly formatted?\n")
        return

    url = f"https://api.github.com/gists/{GistID}"
    headers = {
        "Authorization": f"token {GithubToken}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            gist_data = response.json()
            if "events.txt" in gist_data["files"]:
                remote_content = gist_data["files"]["events.txt"]["content"]
                
                with open(eventsFile, "w") as file:
                    file.write(remote_content)
                
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(logFile, "a") as f:
                    f.write(f"[{now}] [INF]: Startup Cloud Sync Successful!\n")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(logFile, "a") as f:
                f.write(f"[{now}] [ERR]: Startup Sync Failed! Status: {response.status_code}\n")
    except Exception as e:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(logFile, "a") as f:
            f.write(f"[{now}] [ERR]: Startup network exception: {e}\n")

def loadEvents(year, month, day):
    # Load events
    targetDate = f"{year}-{month}-{day}"
    matchedEvents = []

    if not os.path.exists(eventsFile):
        return matchedEvents
    
    with open(eventsFile, "r") as file:
        for line in file:
            cleanLine = line.strip()

            if not cleanLine:
                continue

            parts = cleanLine.split(" | ")

            if str(year) == parts[0] and str(month) == parts[1] and str(day) == parts[2] and parts[7] == "Never":
                matchedEvents.append(parts)
            elif parts[7] == "Daily":
                matchedEvents.append(parts)
            elif parts[7] == "Weekly":
                originDate = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                currentDate = datetime(year, month, day)

                if currentDate >= originDate:
                    deltaDates = (currentDate - originDate).days

                    if deltaDates % 7 == 0:
                        matchedEvents.append(parts)
            elif parts[7] == "Monthly":
                originDate = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                currentDate = datetime(year, month, day)

                if str(day) == parts[2]:
                    if currentDate >= originDate:
                        matchedEvents.append(parts)
            elif parts[7] == "Yearly":
                originDate = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                currentDate = datetime(year, month, day)

                if str(month) == parts[1] and str(day) == parts[2]:
                    if currentDate >= originDate:
                        matchedEvents.append(parts)

    return matchedEvents

def nextEvent():
    currentDay = datetime.now().day
    
    minsPastMidnight = (datetime.now().hour * 60) + datetime.now().minute
    
    eventsToday = loadEvents(currentYear, currentMonthNum, currentDay)
    
    futureEvents = []
    
    for event in eventsToday:
        startTimeStr = event[3]
        
        timeParts = startTimeStr.split(":")
        
        totalMins = (int(timeParts[0]) * 60) + int(timeParts[1])
        
        if totalMins > minsPastMidnight:
            futureEvents.append(event)
    if len(futureEvents) > 0:
        futureEvents.sort(key=lambda x: x[3])
        return futureEvents[0]
    else:
        return None

def updateNextEvent():
    futureEvent = nextEvent()
    if futureEvent is not None:
        eventName = futureEvent[5]
        eventSTime = futureEvent[3]
        upNextTitle.configure(text=f"{eventName} ({eventSTime})")
    else:
        upNextTitle.configure(text="No More Events Today")
    root.after(60000, updateNextEvent)


def showEventMenu(event=None):
    global calWindow

    eventMaker = ctk.CTkToplevel(calWindow)
    
    screenW = eventMaker.winfo_screenwidth()
    screenH = eventMaker.winfo_screenheight()
    winW = 280
    winH = 350
    winX = (screenW // 2) - (winW // 2)
    winY = (screenH // 2) - (winH // 2)
    
    eventMaker.geometry(f"{winW}x{winH}+{winX}+{winY}")
    eventMaker.attributes("-topmost", True)
    eventMakerFrame = ctk.CTkFrame(eventMaker, fg_color="#1f2c3f", corner_radius=12)
    eventMakerFrame.pack(fill="both", expand="True")
    eventMakerFrame.grid_columnconfigure(1, weight=1)
    eventMaker.title("Event Maker")
    eventMaker.overrideredirect(True)
    
    ctk.CTkLabel(eventMakerFrame, text="Event Name:").grid(row=0, column=0, padx=5, pady=5)
    ctk.CTkLabel(eventMakerFrame, text="Event Notes:").grid(row=1, column=0, padx=5, pady=5)
    ctk.CTkLabel(eventMakerFrame, text="Start Time:").grid(row=2, column=0, padx=5, pady=5)
    ctk.CTkLabel(eventMakerFrame, text="End Time:").grid(row=2, column=1, padx=5, pady=5)
    ctk.CTkLabel(eventMakerFrame, text="Repeat:").grid(row=4, column=0, padx=5, pady=5)
    ctk.CTkLabel(eventMakerFrame, text="Color:").grid(row=5, column=0, padx=5, pady=5)
    eventNamer = ctk.CTkEntry(eventMakerFrame, placeholder_text="New Event")
    eventNoteer = ctk.CTkEntry(eventMakerFrame, placeholder_text="Lorem Ipsum")
    eventSTimeFrame = ctk.CTkFrame(eventMakerFrame, fg_color=trans)
    eventETimeFrame = ctk.CTkFrame(eventMakerFrame, fg_color=trans)
    eventSTimeH = ctk.CTkComboBox(eventSTimeFrame, values=[f"{h:02d}" for h in range(24)], width=60)
    eventSTimeM = ctk.CTkComboBox(eventSTimeFrame, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
    eventETimeH = ctk.CTkComboBox(eventETimeFrame, values=[f"{h:02d}" for h in range(24)], width=60)
    eventETimeM = ctk.CTkComboBox(eventETimeFrame, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
    eventRepeater = ctk.CTkComboBox(eventMakerFrame, values=["Never","Daily","Weekly","Monthly","Yearly"])
    eventColoriser = ctk.CTkComboBox(eventMakerFrame, values=["Default Dark","Google Blue","Google Green","Google Yellow","Google Red","IMPORTANT"])
    errorLbl = ctk.CTkLabel(eventMakerFrame, text="", text_color="#5c1e1e", font=("Arial", 12, "bold"))

    def saveEvent():
        year = yearSel.get()
        month = months.index(monthSel.get()) + 1
        day = activeDayNum
        stime = f"{eventSTimeH.get()}:{eventSTimeM.get()}"
        etime = f"{eventETimeH.get()}:{eventETimeM.get()}"
        STimeMin = int(eventSTimeH.get()) * 60 + int(eventSTimeM.get())
        ETimeMin = int(eventETimeH.get()) * 60 + int(eventETimeM.get())
        
        if ETimeMin <= STimeMin:
            errorLbl.configure(text="End time must be after start time!", text_color="#ff3333")
            return
        
        name = eventNamer.get()
        note = eventNoteer.get()
        repeat = eventRepeater.get()
        color = noteColors[eventColoriser.get()]
        newEventOrdered = [str(year), str(month), str(day), stime, etime, name, note, repeat, color]
        newEventFormatted = " | ".join(newEventOrdered) + "\n"

        with open(eventsFile, "a") as file:
            file.write(newEventFormatted)

        eventMaker.destroy()
        syncGist()
        closeDayView()
        dateChange(None)
        openDayView(activeDayNum)

    cancelBtn = ctk.CTkButton(eventMakerFrame, text="Cancel", width=100, command=eventMaker.destroy)
    saveBtn = ctk.CTkButton(eventMakerFrame, text="Save", width=100, command=saveEvent)
    eventNamer.grid(row=0, column=1, padx=5, pady=5)
    eventNoteer.grid(row=1, column=1, padx=5, pady=5)
    eventRepeater.grid(row=4, column=1, padx=5, pady=5)
    eventSTimeFrame.grid(row=3, column=0, padx=5, pady=5)
    eventETimeFrame.grid(row=3, column=1, padx=5, pady=5)
    eventSTimeH.pack(side="left", padx=2)
    eventSTimeM.pack(side="left", padx=2)
    eventETimeH.pack(side="left", padx=2)
    eventETimeM.pack(side="left", padx=2)
    eventColoriser.grid(row=5, column=1, padx=5, pady=5)
    errorLbl.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
    cancelBtn.grid(row=7, column=0, padx=5, pady=20)
    saveBtn.grid(row=7, column=1, padx=5, pady=20)

def removeEvent(targetEvent):
    wantedPoster = " | ".join(targetEvent)
    with open(eventsFile, "r") as file:
        suspects = file.readlines()
        with open(eventsFile, "w") as betterFile:
            for suspect in suspects:
                if suspect.strip() == wantedPoster:
                    continue
                else:
                    betterFile.write(suspect)
    syncGist()
    closeDayView()
    dateChange(None)
    openDayView(activeDayNum)

def openDayView(dayNum):
    global eventListbox, datebg, calbg, backBtn, activeDayNum, newEventBtn
    activeDayNum = dayNum
    thisYearNum = int(yearSel.get())
    thisMonthNum = months.index(monthSel.get()) + 1
    
    datebg.pack_forget()
    backBtn.pack(side="left", padx=5)
    newEventBtn.pack(side="left", padx=5)
    
    eventListbox = ctk.CTkScrollableFrame(calbg, fg_color="#2a3e5c", corner_radius=12)
    eventListbox.pack(fill="both", expand=True, padx=10, pady=10)
    
    dayEvents = loadEvents(thisYearNum, thisMonthNum, dayNum)
    
    dayEvents.sort(key=lambda x: (x[3], x[5]))
    
    for event in dayEvents:
        displayText = f"{event[3]} - {event[4]} | {event[5]}"
        noteText = f"{event[6]}"
        bgHex = event[8] if len(event) > 8 else "#1f2c3f"
        eventFrame = ctk.CTkFrame(eventListbox, fg_color=bgHex, corner_radius=12)
        eventFrame.grid_columnconfigure(0, weight=1)  # Gives text column all the free space
        eventFrame.grid_columnconfigure(1, weight=0)  # Keeps button column tightly sized
        lbl = ctk.CTkLabel(eventFrame, text=displayText, anchor="w")
        notes = ctk.CTkLabel(eventFrame, text=noteText, anchor="w", wraplength=220, justify="left",)
        deleteBtn = ctk.CTkButton(eventFrame, text="X", fg_color=bgHex, width=30, height=30, hover_color="#5c1e1e", anchor="n", command=lambda e=event: removeEvent(e))
        lbl.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        deleteBtn.grid(row=0, column=1, padx=10, pady=5, sticky="ne")
        notes.grid(row=1, column=0, padx=10, columnspan=2, pady=(0, 5), sticky="w")
        eventFrame.pack(fill="x", padx=10, pady=5)

def closeDayView():
    global eventListbox, datebg, newEventBtn, backBtn
    if eventListbox is not None:
        eventListbox.pack_forget()
        eventListbox.destroy()
    backBtn.pack_forget()
    newEventBtn.pack_forget()
    datebg.pack(fill="both", expand=True, padx=10, pady=10)

def drawCal(parent, year, month):
    global calendarDays
    
    today = datetime.now()
    thisYear = today.year
    thisMonth = today.month
    thisDay = today.day

    for btn in calendarDays:
        btn.grid_forget()
        btn.destroy()
    calendarDays.clear()
    
    important_days = set()
    
    if os.path.exists(eventsFile):
        with open(eventsFile, "r") as file:
            for line in file:
                cleanLine = line.strip()
                if not cleanLine:
                    continue
                
                parts = cleanLine.split(" | ")
                
                # 1. Check array length first to prevent IndexError
                if len(parts) < 9:
                    continue  
                    
                # 2. Skip if it's not marked IMPORTANT
                if parts[8] != "#9500ff":
                    continue  
                
                # 3. Wrap date conversion in a try block to prevent structural crashes
                try:
                    ev_year, ev_month, ev_day = int(parts[0]), int(parts[1]), int(parts[2])
                    ev_repeat = parts[7]
                    
                    for d in range(1, 32):
                        try:
                            currentDate = datetime(year, month, d)
                            originDate = datetime(ev_year, ev_month, ev_day)
                            if currentDate < originDate:
                                continue
                            
                            if ev_repeat == "Never" and year == ev_year and month == ev_month and d == ev_day:
                                important_days.add(d)
                            elif ev_repeat == "Daily":
                                important_days.add(d)
                            elif ev_repeat == "Weekly" and (currentDate - originDate).days % 7 == 0:
                                important_days.add(d)
                            elif ev_repeat == "Monthly" and d == ev_day:
                                important_days.add(d)
                            elif ev_repeat == "Yearly" and month == ev_month and d == ev_day:
                                important_days.add(d)
                        except ValueError:
                            continue
                except (ValueError, IndexError):
                    continue

    weeks = calendar.monthcalendar(year, month)
    
    for wInd, week in enumerate(weeks):
        for dInd, dayNum in enumerate(week):
            if dayNum > 0:
                if year == thisYear and month == thisMonth and dayNum == thisDay:
                    dayCol = "#ff9900"
                    dayColH = "#c27706"
                else:
                    dayCol = "#1F6AA5"
                    dayColH = "#144870"
                if dayNum in important_days:
                    b_width = 2
                    b_color = "#9500ff"
                else:
                    b_width = 0
                    b_color = dayCol
                
                btn = ctk.CTkButton(parent, text=str(dayNum), width=32, height=32, fg_color=dayCol, border_width=b_width, border_color=b_color, hover_color=dayColH, command=lambda d=dayNum: openDayView(d))
                btn.grid(row=wInd + 1, column=dInd, padx=2, pady=2)
                calendarDays.append(btn)
    
def dateChange(choice):
    global datebg
    monthNum = months.index(monthSel.get()) + 1
    yearNum = int(yearSel.get())
    drawCal(datebg, yearNum, monthNum)

def setup():

    #Function that actually sets up the menu
    global calWindow, datebg, monthSel, yearSel, backBtn, calbg, newEventBtn
    calWindow = ctk.CTkToplevel(root)
    
    #Hide the shitty frame Windows puts around windows because it sucks
    root.overrideredirect(True)
    calWindow.overrideredirect(True)
    calWindow.config(bg=trans)
    calWindow._fg_color = trans

    menuW = 320
    menuH = 450
    calW = 320
    calH = 350

    screenW = root.winfo_screenwidth()
    screenH = root.winfo_screenheight()

    menuX = 15
    menuY = screenH - menuH - 60
    calY = menuY - calH - 10

    root.attributes("-topmost", True)
    calWindow.attributes("-topmost", True)

    root.geometry(f"{menuW}x{menuH}+{menuX}+{menuY}")
    calWindow.geometry(f"{calW}x{calH}+{menuX}+{calY}")

    root.focus_force()

    if hasattr(root, "_canvas"):
        root._canvas.config(bg=trans)

    root.wm_attributes("-transparentcolor", trans)
    
    if hasattr(calWindow, "_canvas"):
        calWindow._canvas.config(bg=trans)

    calWindow.wm_attributes("-transparentcolor", trans)
    
    outer_frameCal = ctk.CTkFrame(calWindow, fg_color=trans, corner_radius=0)
    outer_frameCal.pack(fill="both", expand=True)

    calbg = ctk.CTkFrame(outer_frameCal, fg_color="#1f2c3f", corner_radius=12, border_width=1, border_color="#333333")
    calbg.pack(fill="both", expand=True, padx=5, pady=5)
 
    calHead = ctk.CTkFrame(calbg, fg_color="transparent")
    calHead.pack(fill="x", padx=10, pady=10)
    newEventBtn = ctk.CTkButton(calHead, text="+", width=30, command=showEventMenu)
    backBtn = ctk.CTkButton(calHead, text="←", width=30, command=closeDayView)
    monthSel = ctk.CTkComboBox(calHead, values=months, width=100)
    monthSel.pack(side="left", padx=5, pady=5)
    monthSel.set(currentMonth)
    yearSel = ctk.CTkComboBox(calHead, values=yearRange, width=100)
    yearSel.pack(side="left", padx=5, pady=5)
    yearSel.set(str(currentYear))
    
    monthSel.configure(command=dateChange)
    yearSel.configure(command=dateChange)
    
    datebg = ctk.CTkFrame(calbg, fg_color="#2a3e5c", corner_radius=12)
    datebg.pack(fill="both", expand=True, padx=10, pady=10)
    
    for index, dayName in enumerate(days):
        lbl = ctk.CTkLabel(datebg, text=dayName)

        lbl.grid(row=0, column=index, padx=5, pady=5)

    for i in range(7):
        datebg.grid_columnconfigure(i, weight=1)

    drawCal(datebg, currentYear, currentMonthNum)

def openTkEX():
    #Open TkEX
    subprocess.Popen([sys.executable, "TkinterEX\\tkinterex_1.0.pyw"])
    root.after(10, showToggle)

def kill():
    #End the program
    global trayIcon

    if trayIcon is not None:
        trayIcon.stop()

    root.destroy()

def hide(event):
    #Hide the program window
    root.withdraw()

def forceFocus():
    #Why do I even keep this, it doesn't work I don't think?
    root.attributes("-topmost", True)
    root.deiconify()
    root.lift()

    root.focus_force()

def showToggle():
    #Hide the program window but better because it works
    if root.winfo_viewable():
        root.withdraw()
        calWindow.withdraw()
    else:
        root.attributes("-topmost", True)
        root.deiconify()
        root.lift()
        calWindow.attributes("-topmost", True)
        calWindow.deiconify()
        calWindow.lift()
        root.after(10, forceFocus)

def openTrayIco():
    #Make the tray icon
    iconPath = os.path.join(ownFolder, "Icon.png")
    image = Image.open(iconPath)
    return image

def onAction(icon, item):
    #Make the tray icon actually work
    if str(item) == "Toggle Menu":
        root.after(0, showToggle)
    elif str(item) == "Quit":
        root.after(0, kill)

def setupTray():
    #Make harder, do it better!
    global trayIcon
    iconImg = openTrayIco()

    menu = pystray.Menu(
        pystray.MenuItem("Toggle Menu", onAction),
        pystray.MenuItem("Quit", onAction)
    )

    trayIcon = pystray.Icon("Prootils", iconImg, "Proto Utils", menu)
    trayIcon.run()

def loadW3Sch():
    #Load W3Schools
    url = "https://www.w3schools.com/"
    webbrowser.open(url)
    showToggle()

def loadGDrive():
    #Load Google Drive
    url = "https://drive.google.com/drive/u/0/home"
    webbrowser.open(url)
    showToggle()

def loadTracker():
    #Load Course Tracker
    url = "https://docs.google.com/spreadsheets/d/13v6cMvqTPFAp4PH_lWr5JiBCf9-Ke3-wB0BEc7pormA/edit?gid=0#gid=0"
    webbrowser.open(url)
    showToggle()

outer_frame = ctk.CTkFrame(root, fg_color=trans, corner_radius=0)
outer_frame.pack(fill="both", expand=True)

rootbg = ctk.CTkFrame(outer_frame, fg_color="#1f2c3f", corner_radius=12, border_width=1, border_color="#333333")
rootbg.pack(fill="both", expand=True, padx=5, pady=5)

TkEX = ctk.CTkButton(rootbg, text="TkinterEX", command=openTkEX)
TkEX.grid(column=0, row=0, padx=15, pady=15)

w3s = ctk.CTkButton(rootbg, text="W3Schools", command=loadW3Sch)
w3s.grid(column=0, row=1, padx=15, pady=15)

GD = ctk.CTkButton(rootbg, text="Google Drive", command=loadGDrive)
GD.grid(column=0, row=2, padx=15, pady=15)

Tracker = ctk.CTkButton(rootbg, text="Course Tracker", command=loadTracker)
Tracker.grid(column=0, row=3, padx=15, pady=15)

oncomingEvents = ctk.CTkFrame(rootbg, fg_color="#2a3e5c", corner_radius=12)
oncomingEvents.grid(row=4, column=0, padx=5, pady=5)

upNextHeader = ctk.CTkLabel(oncomingEvents, text="UP NEXT", font=("Arial", 11, "bold"), text_color="#aaaaaa")
upNextHeader.pack(anchor="w", padx=10, pady=(5, 0)) # anchor="w" aligns text to the left side

upNextTitle = ctk.CTkLabel(oncomingEvents, text="No Upcoming Events", font=("Arial", 13, "bold"))
upNextTitle.pack(anchor="w", padx=10, pady=(0, 5))

killButton = ctk.CTkButton(rootbg, text="X", command=showToggle, width=25, height=25)
killButton.place(x=320-25-20, y=15)

trayThread = threading.Thread(target=setupTray, daemon=True)
trayThread.start()

root.after(150, setup)

root.after(200, updateNextEvent)

keyboard.add_hotkey("ctrl+alt+/", lambda: root.after(0, showToggle))

downloadGist()

root.mainloop()