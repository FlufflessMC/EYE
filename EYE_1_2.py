import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Tk, Button, PhotoImage
import os
import cv2
import pyautogui
import numpy as np
import pygetwindow as gw
import configparser
import threading
import time
import sys
import shutil
import webbrowser
from tkinter import simpledialog

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def get_executable_dir():
    """Get the directory where the executable or script resides."""
    if getattr(sys, 'frozen', False):
        # Running as a compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as a normal script
        return os.path.dirname(os.path.abspath(__file__))

executable_dir = get_executable_dir()

# Directories for categories, trigger, and screenshots
config_file = os.path.join(executable_dir, 'config.ini')  # Use resource_path here
CATEGORIES_FOLDER = os.path.join(executable_dir, "categories")
SCREENSHOTS_FOLDER = os.path.join(executable_dir, "screenshots")
TRIGGER_FOLDER = os.path.join(executable_dir, "Trigger")
stop_detection_event = threading.Event()

# Create these directories if they don't exist
for folder in [CATEGORIES_FOLDER, SCREENSHOTS_FOLDER, TRIGGER_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    if not os.path.exists(config_file):
        sample_config = configparser.ConfigParser()
        sample_config['Parameters'] = {
            'WindowTitle': 'YourWindowTitle',
        }
        #sample_config['SampleCategory'] = {}
        
        with open(config_file, 'w') as configfile:
            sample_config.write(configfile)

#create_folders_and_config()

class ToolTip(object):
    def __init__(self, widget, text='widget info', delay=1000):  # delay in milliseconds
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.delay = delay
        self.x = self.y = 0

        self.widget.bind("<Enter>", self.schedule_tip)
        self.widget.bind("<Leave>", self.cancel_tip)

    def schedule_tip(self, event):
        self.id = self.widget.after(self.delay, lambda: self.show_tip(event))

    def cancel_tip(self, event):
        if self.id:
            self.widget.after_cancel(self.id)
        self.id = None
        self.hide_tip(event)

    def show_tip(self, event):
        "Display text in tooltip window"
        self.x = event.x + self.widget.winfo_rootx() + 20
        self.y = event.y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (self.x, self.y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#403e3e", relief=tk.SOLID, borderwidth=1, fg="white",
                         font=("Roboto", "9", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()




class MainFrame:
    def __init__(self, root, config_file, tab_name):
        self.root = root
        root.minsize(width=252, height=45)
        root.maxsize(width=252, height=4000)
        config_file = "config.ini"
        config = configparser.ConfigParser()
        config.read(config_file)
        self.config_file = config_file
        
        #self.start_time = time.time()  # Record the start time
        
        #self.root.after(1000, self.check_elapsed_time)  # Check elapsed time every second
        
        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=3, column=0, columnspan=2)
        
        #self.detection_threads = []
        self.detection_threads = [None] * len(tab_names)
        self.detection_tabs = []  # Create an empty list to store detection tabs
                                          
        for i, tab_name in enumerate(tab_names, start=1):
            detection_tab = DetectionTab(self.notebook, tab_name, self.config_file, self, self.detection_threads[i - 1], root)
            self.detection_tabs.append(detection_tab)
           
        

        self.setup_gui()
        
        self.load_last_settings()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.detection_running = False 
        self.stop_detection_event = threading.Event()
        
        self.category_db = {}
        
        self.load_parameters_from_ini(self.config_file)
    
    
    
    def setup_gui(self):  
        button_frame = tk.Frame(self.root, bg="#403e3e")
        for i in range(5):  # Assuming you have 5 columns to use
            button_frame.columnconfigure(i, weight=1)
        button_frame.grid(row=0, column=0, sticky="ew")
        
        setgame_frame = tk.Frame(self.root, bg="#403e3e")
        setgame_frame.grid(row=1, column=0, sticky="w")
        
        speed_frame = tk.Frame(self.root, bg="#403e3e")
        speed_frame.grid(row=2, column=0, sticky="w", pady="5")
        
        tabselect_frame = tk.Frame(self.root, bg="#403e3e")
        tabselect_frame.grid(row=3, column=0, sticky="w")
        
        roi_frame = tk.Frame(self.root, bg="#403e3e")
        roi_frame.grid(row=4, column=0, sticky="w")
        
        

        self.start_button = tk.Button(button_frame, image=Img_Play, command=self.toggle_detection, relief="flat", borderwidth=0, highlightthickness=0)
        self.start_button.grid(row=0, column=0, sticky="w", pady=1, padx=3)
        self.start_button.config(state="normal")
        ToolTip(self.start_button, "Start the process", delay=1000)
        
        self.new_button = tk.Button(button_frame, image=Img_New, command=self.create_new, relief="flat", borderwidth=0, highlightthickness=0)
        self.new_button.grid(row=0, column=3, sticky="w", pady=1, padx=3)
        ToolTip(self.new_button, "Reset everything", delay=1000)
        
        self.fluffy_button = tk.Button(button_frame, image=Img_Fluffy, command=self.open_link, relief="flat", borderwidth=0, highlightthickness=0)
        self.fluffy_button.grid(row=0, column=4, sticky="w", pady=1, padx=3)
        ToolTip(self.fluffy_button, "Tutorial", delay=1000)
      
        save_button = tk.Button(button_frame, image=Img_Save, command=self.save_data, relief="flat", borderwidth=0, highlightthickness=0)
        save_button.grid(row=0, column=1, sticky="w", pady=1, padx=3)
        ToolTip(save_button, "Save", delay=1000)
        
        load_button = tk.Button(button_frame, image=Img_Load, command=self.load_data, relief="flat", borderwidth=0, highlightthickness=0)
        load_button.grid(row=0, column=2, sticky="w", pady=1, padx=3)
        ToolTip(load_button, "Load", delay=1000)
        
        
        self.speed_scale = tk.Scale(speed_frame, from_=0.0, to=1.0, resolution=0.1, orient=tk.HORIZONTAL, command=self.update_sleep_time, length=240, bg="#403e3e", relief="flat", borderwidth=0, highlightthickness=0, showvalue=0)
        self.speed_scale.set(0.5)  # Default value
        self.speed_scale.grid(row=0, column=0, columnspan=3, sticky="ew", padx="7")
        ToolTip(self.speed_scale, "Cycle Interval: Shorter intervals increase speed but consume more CPU resources", delay=1000)
        
        
        self.window_title_entry = tk.Entry(setgame_frame, width=25, bg="#403e3e", fg="white", font=("Roboto", 9), relief="flat")
        self.window_title_entry.grid(row=0, column=1, sticky="ew", pady=1, padx=2)
        
        set_game_window_button = tk.Button(setgame_frame, image=Img_Setgame, command=self.show_windows, relief="flat", borderwidth=0, highlightthickness=0)
        set_game_window_button.grid(row=0, column=0, sticky="ew", pady=1, padx=3)
        ToolTip(set_game_window_button, "Select the Window for Monitoring", delay=1000)
        
        self.notebook = ttk.Notebook(tabselect_frame)
        self.notebook.grid(row=0, column=0, columnspan=5)
        
        
        log_frame = ttk.Frame(self.root)
        log_frame.grid(row=6, column=0, columnspan=4, sticky="w", pady=3, padx=2)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, width=29, height=120, bg="#403e3e", fg="white", font=("Roboto", 9), relief="flat")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        placeholder_text = "Log"
        self.log_text.insert("1.0", placeholder_text, "placeholder")
        self.log_text.tag_configure("placeholder", foreground="grey")
        self.log_text.bind("<FocusIn>", self.remove_placeholder)
    
    
    def log(self, message):
        self.log_text.configure(state='normal')  # Enable text widget for editing
        self.log_text.insert(tk.END, message + '\n')  # Append the message
        self.log_text.configure(state='disabled')  # Disable editing after appending
        self.log_text.see(tk.END)  # Auto-scroll to the end


    def update_sleep_time(self, new_value):
        self.log(f"Slider updated: {new_value}")

    
    def open_link(self):
        url = "https://discord.gg/FEe9wzVJ9N" 
        webbrowser.open(url)
    
    def save_data(self, event=None):
        ini_file = filedialog.asksaveasfilename(filetypes=[("INI-Dateien", "*.ini")], defaultextension=".ini")

        if ini_file:
            if not ini_file.endswith('.ini'):
                ini_file += '.ini'

        if ini_file:
            config = configparser.ConfigParser()

            # Speichern der Allgemeinen Parameter
            config['Parameters'] = {
                'WindowTitle': self.window_title_entry.get(),
                'ScaleValue': str(self.speed_scale.get()),
            }

            for tab in self.detection_tabs:
                tab_name = tab.tab_name  # Tab-Name verwenden
                config[tab_name] = {'ROI': tab.roi_entry.get(),
                                    'Threshold': tab.threshold_scale.get()
                                    }  
                
                # Fügen Sie die Kategorien als separate Abschnitte hinzu
                for category in tab.category_db:
                    config[tab_name][category] = ''  # Fügen Sie die Kategorie in den Tab-Abschnitt ein

            #for i, tab in enumerate(self.detection_tabs, start=1):
             #   tab_name = tab.tab_name
              #  config[tab_name]['ROI'] = tab.roi_entry.get()
            
            with open(ini_file, 'w') as configfile:
                config.write(configfile)
  
    def on_closing(self):
        self.stop_detection_event.set() 
        self.start_button.config(text="Start")
        self.log("Detection stopping...")
        for detection_thread in self.detection_threads:
            if detection_thread is not None and detection_thread.is_alive():
                detection_thread.stopped = True
        
        ini_file = "config.ini"  # Setzen Sie den Dateinamen Ihrer INI-Datei
        config = configparser.ConfigParser()

        config['Parameters'] = {
                'WindowTitle': self.window_title_entry.get(),
                'ScaleValue': str(self.speed_scale.get()),
            }
        
        for tab in self.detection_tabs:
            tab_name = tab.tab_name
            config[tab_name] = {'ROI': tab.roi_entry.get(),
                                'Threshold': tab.threshold_scale.get()
                                }  # Erstellen Sie einen Abschnitt für den Tab und speichern Sie den ROI-Wert

            # Fügen Sie die Kategorien als separate Abschnitte hinzu
            for category in tab.category_db:
                config[tab_name][category] = ''  # Fügen Sie die Kategorie in den Tab-Abschnitt ein

       # Speichern Sie die ROIs für jeden Tab
        for i, tab in enumerate(self.detection_tabs, start=1):
            tab_name = tab.tab_name
            config[tab_name]['ROI'] = tab.roi_entry.get()

        # Schreiben Sie die INI-Datei
        with open(ini_file, 'w') as configfile:
            config.write(configfile)

        self.root.destroy() 


    def load_data(self, event=None):
        ini_file = filedialog.askopenfilename(filetypes=[("INI Files", "*.ini")])
        if ini_file:
            # Copy the content of the selected INI file to the config.ini
            shutil.copy(ini_file, "config.ini")
            print("Content from the selected INI file has been copied to config.ini")
            self.load_parameters_from_ini(ini_file)
        
              
    def load_parameters_from_ini(self, ini_file):
        config = configparser.ConfigParser()
        if os.path.exists(ini_file):
            config.read(ini_file)
            self.populate_gui_from_ini(config)
   
    def populate_gui_from_ini(self, config):
        parameters = config['Parameters']
        self.window_title_entry.delete(0, tk.END)
        self.window_title_entry.insert(0, parameters.get('WindowTitle', ''))
        # Load and set the scale value
        scale_value = parameters.get('ScaleValue')
        if scale_value is not None:
            try:
                self.speed_scale.set(float(scale_value))
            except ValueError:
                pass  # Handle or log error if the value in the file is not a valid float

        for detection_tab in self.detection_tabs:
            tab_name = detection_tab.tab_name

            if tab_name in config:
                tab_section = config[tab_name]

                # Load tab-specific settings like Threshold
                detection_tab.load_tab_settings_from_ini()

                # Clear existing categories to avoid duplicates
                detection_tab.category_db.clear()

                # Iterate through the keys in this section, adding only categories
                for key in tab_section:
                    if key != 'threshold':  # Skip the Threshold key
                        detection_tab.category_db[key] = tab_section[key]

                # Update the category listbox for the tab
                detection_tab.update_category_listbox()     
           
                threshold_value = tab_section.get('threshold')
                if threshold_value is not None:
                    try:
                        detection_tab.threshold_scale.set(float(threshold_value))  # Direkter Zugriff auf das Attribut der Instanz
                    except ValueError:
                        pass  # Handle or log error if the value in the file is not a valid float
        




        #for detection_tab in self.detection_tabs:
         #   detection_tab.load_tab_settings_from_ini()
          #  for section in config.sections():
           #     
            #    if section != 'Parameters' and section !='threshold' and section in tab_names:
             #       self.detection_tabs[int(section) - 1].category_db[section] = {}
              #      self.detection_tabs[int(section) - 1].update_category_listbox()

          
    def load_last_settings(self, event=None):
        if os.path.exists(self.config_file):
            config = configparser.ConfigParser()
            config.read(self.config_file)
            self.populate_gui_from_ini(config)


    def create_new(self):
        sample_config = configparser.ConfigParser()
        if os.path.exists(config_file):
            os.remove(config_file)

        sample_config['Parameters'] = {
            'WindowTitle': 'YourWindowTitle',
        }
        
        with open(config_file, 'w') as configfile:
            sample_config.write(configfile)
       
        for tab in self.detection_tabs:
            tab.category_db = {}  
            tab.update_category_listbox() 
            tab.roi_entry.delete(0, tk.END)
        self.load_last_settings(config_file)
       
       
    def start_detection(self):
        # Retrieve and store the current speed value
        current_speed = float(self.speed_scale.get())
        for detection_tab in self.detection_tabs:
            self.roi_input = detection_tab.roi_entry.get()
            self.roi_values = self.roi_input.split()
            if not detection_tab.detection_thread or not detection_tab.detection_thread.is_alive():
                # Pass the current speed to the detection_tab
                detection_tab.current_speed = current_speed
            if len(self.roi_values) != 4:
                self.log(f"{detection_tab.tab_name} not set up (disabled).")
            else:
                if detection_tab.detection_thread and detection_tab.detection_thread.is_alive():
                    self.log(f"Detection thread for tab {detection_tab.tab_name} is already running.")
                else:
                    detection_thread = threading.Thread(target=detection_tab.detection_loop)
                    detection_thread.daemon = True
                    detection_thread.stopped = False
                    detection_tab.set_detection_thread(detection_thread)  # Set the detection thread for the tab
                    detection_thread.start()
                    self.detection_threads.append(detection_thread)  # Add the thread to the list
        # Disable the speed scale
        self.speed_scale.config(state="disabled")
        
        self.start_button.config(text="Stop")
        self.log("Detection started")
        self.detection_running = True

    def stop_detection(self):
        self.stop_detection_event.set() 
        
        # Re-enable the speed scale
        self.speed_scale.config(state="normal")
        
        self.start_button.config(text="Start")
        self.log("Detection stopping...")
        for detection_thread in self.detection_threads:
            if detection_thread is not None and detection_thread.is_alive():
                detection_thread.stopped = True
                
        self.detection_running = False

    def toggle_detection(self):
        if self.detection_running:
            self.stop_detection()
            self.start_button.config(image=Img_Play)
            
        else:
            self.start_detection()
            self.start_button.config(image=Img_Stop)
            
    

    def show_windows(self):
        self.window_titles = gw.getAllTitles()
        self.window_title_listbox = None
        self.populate_window_titles_listbox()
    
    def populate_window_titles_listbox(self):
        self.window_title_listbox = tk.Toplevel(self.root)
       # self.window_title_listbox.configure(bg="#403e3e")
        
        listbox = tk.Listbox(self.window_title_listbox, bg="#403e3e", fg="white", font=("Roboto", 9))
        listbox.pack()
        
        for title in self.window_titles:
            if title.strip():
                listbox.insert(tk.END, title)
        listbox.bind('<<ListboxSelect>>', self.select_window_title)

                
    def select_window_title(self, event):
        selected_index = event.widget.curselection()
        if selected_index:
            selected_title = event.widget.get(selected_index[0])
            self.window_title_entry.delete(0, tk.END)
            self.window_title_entry.insert(0, selected_title)
            self.window_title_listbox.destroy()

    def remove_placeholder(self, event=None):
        current_text = self.log_text.get("1.0", "end-1c")
        if current_text.strip() == "Log":
            self.log_text.delete("1.0", "end")
            self.log_text.tag_remove("placeholder", "1.0", "end")
        
    def update_log_text(self):
        self.log_text.update_idletasks()
        
    def log(self, message):
        self.remove_placeholder()
        log_text = self.log_text
        log_text.config(state=tk.NORMAL)  # Allow modifying the text widget
        log_text.insert("1.0", message + "\n")  # Insert the new log message at the beginning
        log_text.see("1.0")  # Scroll to the new log message
        log_text.config(state=tk.DISABLED)  # Disable editing the text widget
        

class DetectionTab:
    def __init__(self, notebook, tab_name, config_file, MainFrame, detection_thread, root):
        self.root = root 
        self.notebook = notebook
        #self.tab = ttk.Frame(notebook)
        #notebook.add(self.tab, text=tab_name)
        self.tab_name = tab_name 
        self.mainframe = MainFrame
        self.detection_thread = detection_thread  # Pass the detection_thread to the DetectionTab
        
        
        self.categories_folder = CATEGORIES_FOLDER
        self.screenshots_folder = SCREENSHOTS_FOLDER
        self.trigger_folder = TRIGGER_FOLDER
        
        self.config_file = config_file
        self.category_db = {}
        self.setup_gui()
        
        self.is_tracking = False
        self.mouse_track_id = None
        self.temp_label = None
        
        self.current_speed = 0.5  # default value
        
        

        
    def load_tab_settings_from_ini(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)

        if self.tab_name in config:
            settings = config[self.tab_name]
            # Load tab-specific settings here
            if 'ROI' in settings:
                self.roi_entry.delete(0, tk.END)
                self.roi_entry.insert(0, settings['ROI'])
                # Load other tab-specific settings here    
            # Initialize self.category_db based on the categories in the settings
            self.category_db = {category: {} for category in settings if category != 'ROI'}
        
    def setup_gui(self):    
        
        style = ttk.Style()
        style.configure("Custom.TFrame", background="#403e3e")  # Create a custom style for the ttk.Frame
        style.layout("Custom.Treeview", [('Treeview.field', {'sticky': 'nswe'})])  # Remove the header
        style.configure("Custom.Treeview", background="#403e3e", fieldbackground="#403e3e")  # Set the background color
        
        
        self.tab = ttk.Frame(self.notebook, style="Custom.TFrame")
        self.notebook.add(self.tab, text=self.tab_name)
        self.roi_frame = tk.Frame(self.tab, bg="#403e3e")
        self.roi_frame.grid(row=0, column=0, sticky="w", pady=1, padx=2)
        self.category_frame = tk.Frame(self.tab, bg="#403e3e")
        self.category_frame.grid(row=1, column=0, sticky="w", pady=1, padx=2)
        
        self.roi_entry = tk.Entry(self.roi_frame, width=21, bg="#403e3e", fg="white", font=("Roboto", 9), relief="flat")
        self.roi_entry.grid(row=0, column=1, columnspan=3, sticky="w")
        ToolTip(self.roi_entry, "Observation coodinates, right click to open the folder. Middle click to show coordinates", delay=1000)
        
        self.roi_entry.insert(0, "x, y, width, and height")
        self.roi_entry.config()

        self.roi_entry.bind("<FocusIn>", self.on_roi_entry_focus_in)
        self.roi_entry.bind("<FocusOut>", self.on_roi_entry_focus_out)
        self.roi_entry.bind("<Button-3>", self.open_screenshot_folder)
        self.roi_entry.bind("<Button-2>", self.start_mouse_tracking)

        #sample_screenshot_button = tk.Button(self.tab, text="Area Screenshot", command=self.sample_ROI, width=21, bg="#403e3e", fg="white", font=("Roboto", 9))
        sample_screenshot_button = tk.Button(self.roi_frame, image=Img_Screenshot, command=self.sample_ROI, relief="flat", borderwidth=0, highlightthickness=0)
        sample_screenshot_button.grid(row=0, column=0, sticky="w", pady=1, padx=3)
        sample_screenshot_button.bind('<Button-3>', lambda event: self.start_timer(event))
        ToolTip(sample_screenshot_button, "Make a Screenshot of the current Area. Right Click to delay the screenshot", delay=1000)
        
        self.threshold_scale = tk.Scale(self.roi_frame, from_=20000, to=0, resolution=100, orient="horizontal", command=self.update_threshold, length=240, bg="#403e3e", relief="flat", borderwidth=0, highlightthickness=0, showvalue=0)
        self.threshold_scale.grid(row=1, column=0, columnspan=4,  sticky="w", pady=1, padx=3)
        self.threshold_scale.set(9000) 
        ToolTip(self.threshold_scale, "Set the comparison sensitivity. Lower means higher sensitivity", delay=1000)
        
        
        category_listbox = tk.Listbox(self.category_frame, width=30, height=5, bg="#403e3e", fg="#ff84eb", highlightbackground="#403e3e", highlightcolor="#403e3e", font=("Roboto", 9), relief="flat")
        category_listbox.grid(row=0, column=0, columnspan=2, sticky="w")
        self.category_listbox = category_listbox
        self.category_listbox.bind("<Delete>", self.delete_category)
        self.category_listbox.bind("<BackSpace>", self.delete_category)
        self.category_listbox.bind("<Button-3>", self.open_category_folder)
        
        category_placeholder_text = "no Catergory yet"
        category_listbox.insert(0, category_placeholder_text)
        ToolTip(self.category_listbox, "right click to open the folder", delay=1000)
        
        category_name_entry = tk.Entry(self.category_frame, bg="#403e3e", fg="white", font=("Roboto", 9), relief="flat")
        category_name_entry.grid(row=1, column=0, columnspan=2, sticky="ws")
        self.category_name_entry = category_name_entry
        self.category_name_entry.insert(0, "add category")
        self.category_name_entry.config(fg="gray") 
        self.category_name_entry.bind("<Return>", self.add_category) 
        self.category_name_entry.bind("<FocusIn>", self.on_category_entry_focus_in)
        self.category_name_entry.bind("<FocusOut>", self.on_category_entry_focus_out)

        #self.category_listbox.bind("<<ListboxSelect>>", self.list_category_pictures)
        #picture_listbox = tk.Listbox(self.category_frame, width=13, height=5, bg="#403e3e", fg="#41c4ad", highlightbackground="#403e3e", highlightcolor="#403e3e", font=("Roboto", 9), relief="flat")
        #picture_listbox.grid(row=0, column=2, columnspan=2, sticky="w")
        #self.picture_listbox = picture_listbox
        #picture_placeholder_text = "Select a Catgory"
        #picture_placeholder_text1 = "to show Picturelist"
        #picture_listbox.insert(0, picture_placeholder_text)
        #picture_listbox.insert(1, picture_placeholder_text1)
    
    
    def update_threshold(self, new_value):
        self.mainframe.log(f"Sensitivity: {new_value}")
    
    def start_mouse_tracking(self, event):
        if not self.is_tracking:
            self.is_tracking = True
            # Create a floating label to display coordinates
            self.temp_label = tk.Toplevel()
            self.temp_label.overrideredirect(True)
            self.temp_label_label = tk.Label(self.temp_label, bg="white")
            self.temp_label_label.pack()

            # Start the tracking process
            self.track_mouse()

            # Stop tracking after 5 seconds
            self.roi_entry.after(5000, self.stop_mouse_tracking)
    
    def track_mouse(self):
        x, y = self.roi_entry.winfo_pointerxy()
        self.temp_label.geometry(f"+{x+20}+{y+20}")  # Position the label near the cursor
        self.temp_label_label.config(text=f"{x}, {y}")
        self.mainframe.log(f"Mouse Coordinates: X={x}, Y={y}")

        # Reschedule to track mouse every 100ms
        self.mouse_track_id = self.roi_entry.after(200, self.track_mouse)
    
    def stop_mouse_tracking(self):
        if self.is_tracking:
            self.is_tracking = False
            if self.mouse_track_id is not None:
                self.roi_entry.after_cancel(self.mouse_track_id)
                self.mouse_track_id = None
            if self.temp_label is not None:
                self.temp_label.destroy()
                self.temp_label = None


    def on_focus_in(self, event):
        # Optionally handle window gaining focus
        pass

    def on_focus_out(self, event):
        # Stop mouse tracking when window loses focus
        self.stop_mouse_tracking()

    
    def open_screenshot_folder(self, event):
        # Get the path to the screenshot folder based on your structure.
        screenshot_folder = SCREENSHOTS_FOLDER

        if os.path.exists(screenshot_folder):
            # Open the folder using the default file explorer.
            os.system(f'explorer "{screenshot_folder}"')
        else:
            print(f"Screenshot folder not found: {screenshot_folder}")
    
    def open_category_folder(self, event):
        # Identify the item under the cursor
        clicked_index = self.category_listbox.nearest(event.y)
        
        # Select the item
        self.category_listbox.selection_clear(0, tk.END)
        self.category_listbox.selection_set(clicked_index)
        
        # Get the selected category name.
        selected_category = self.category_listbox.get(clicked_index)

        # Define the path to the category folder based on your structure.
        category_folder = os.path.join(self.categories_folder, selected_category)

        if os.path.exists(category_folder):
            # Open the folder using the default file explorer.
            os.system(f'explorer "{category_folder}"')
        else:
            print(f"Category folder not found: {category_folder}")

 

    def send_error_to_mainframe(self, error_message):
        if self.mainframe:
            self.mainframe.log(error_message)
    
    def add_category(self, event=None):
        category_name = self.category_name_entry.get()
        if category_name == "add category":
            category_name = ""
        if category_name:
            category_folder = os.path.join(self.categories_folder, category_name)
            os.makedirs(category_folder, exist_ok=True)
            self.category_db[category_name] = {}
            self.update_category_listbox()
            self.mainframe.log(f"Category added: {category_name}")
            
    def delete_category(self, event=None):
        selected_category = self.category_listbox.get(tk.ACTIVE)
        if selected_category:
            category_name = selected_category.split(":")[0].strip()
            if category_name in self.category_db:
                confirm = messagebox.askyesno("Delete Category", f"Are you sure you want to delete the category '{category_name}'?")
                if confirm:
                    del self.category_db[category_name]
                    self.update_category_listbox()
                    category_folder = os.path.join(self.categories_folder, category_name.strip())
                    if os.path.exists(category_folder):
                        try:
                            import shutil
                            shutil.rmtree(category_folder)  # Use shutil.rmtree to delete the folder and its contents
                            self.mainframe.log(f"Category folder deleted: {category_folder}")
                        except OSError as e:
                            self.mainframe.log(f"Failed to delete the category folder: {category_folder}")
                            self.mainframe.log(f"Error details: {str(e)}")
                    else:
                        self.mainframe.log(f"Category folder does not exist: {category_folder}")
                    self.mainframe.log(f"Category deleted: {category_name}")


    def update_category_listbox(self):
        num_tabs = len(tab_names)
        self.category_listbox.delete(0, tk.END)
        for category, data in self.category_db.items():
            if category not in ["roi"] + [str(i) for i in range(1, num_tabs + 1)]:
                self.category_listbox.insert(tk.END, category)

    #def list_category_pictures(self, event):
     #   selected_index = self.category_listbox.curselection()
      #  if selected_index:
       #     selected_category = self.category_listbox.get(selected_index)
        #    self.list_category_pictures_for_name(selected_category)

    
    #def list_category_pictures_for_name(self, category_name):
     #   if ":" in category_name:
      #      category_name = category_name.split(":")[0].strip()  # Extract the category name
#
 #       category_folder = os.path.join(self.categories_folder, category_name)
  #      self.picture_listbox.delete(0, tk.END)
   #     picture_files = [f for f in os.listdir(category_folder) if os.path.isfile(os.path.join(category_folder, f))]
    #    for picture_file in picture_files:
     #       self.picture_listbox.insert(tk.END, picture_file)
        
    def on_category_entry_focus_in(self, event):
        if self.category_name_entry.get() == "add category":
            self.category_name_entry.delete(0, tk.END)
            self.category_name_entry.config(fg="white")  

    def on_category_entry_focus_out(self, event):
        if not self.category_name_entry.get():
            self.category_name_entry.insert(0, "add category")
            self.category_name_entry.config(fg="gray")  


    def sample_ROI(self):
        if hasattr(self, 'sample_window') and self.sample_window.winfo_exists():
            self.sample_window.destroy()

        self.roi_input = self.roi_entry.get()
        self.roi_values = self.roi_input.split()
        if len(self.roi_values) != 4:
            self.mainframe.log(f"No Area defined")
        else:
            x, y, width, height = map(int, self.roi_entry.get().split())
            
            
            try:
                sample_screenshot_pil = pyautogui.screenshot(region=(x, y, width, height))
                sample_screenshot_np = np.array(sample_screenshot_pil)
                sample_screenshot_cv = cv2.cvtColor(sample_screenshot_np, cv2.COLOR_RGB2BGR)

                timestamp = time.strftime("%Y%m%d%H%M%S")
                sample_screenshot_filename = os.path.join(self.screenshots_folder, f"sample_screenshot_{timestamp}.png")
                cv2.imwrite(sample_screenshot_filename, sample_screenshot_cv)
                self.display_sample_screenshot(sample_screenshot_filename)
            except Exception as e:
                error_message=(f"An error occurred while capturing the sample screenshot: {e}")
                self.send_error_to_mainframe(error_message)
    
    #def sample_ROI_delay(self):
    #    self.root.after(5000, self.sample_ROI) 
    
    def display_sample_screenshot(self, sample_screenshot_filename):
        self.sample_window = tk.Toplevel(self.root)
        self.sample_window.title("Sample Screenshot")
        sample_screenshot = tk.PhotoImage(file=sample_screenshot_filename)
        screenshot_label = tk.Label(self.sample_window, image=sample_screenshot)
        screenshot_label.image = sample_screenshot
        screenshot_label.pack()
        
    
    def start_timer(self, event):
        # Create a small top-level window
        timer_window = tk.Toplevel(root)
        timer_window.overrideredirect(True)  # Make it borderless
        timer_window.attributes("-topmost", True)  # Keep it on top

        # Position the window near the mouse cursor
        x, y = root.winfo_pointerxy()
        timer_window.geometry(f"+{x+20}+{y+20}")

        # Add a label to show the countdown
        countdown_label = tk.Label(timer_window, text="8")
        countdown_label.pack()

        # Update the timer every second
        self.update_timer(timer_window, countdown_label, 8)


    
    
    def update_timer(self, timer_window, label, remaining):
        if remaining > 0:
            label.config(text=str(remaining))
            timer_window.after(1000, self.update_timer, timer_window, label, remaining - 1)
        else:
            self.sample_ROI()
            timer_window.destroy()
    
        
    def on_roi_entry_focus_in(self, event):
        if self.roi_entry.get() == "x, y, width, and height":
            self.roi_entry.delete(0, tk.END)
            self.roi_entry.config(fg="white")

    def on_roi_entry_focus_out(self, event):
        if not self.roi_entry.get():
            self.roi_entry.insert(0, "x, y, width, and height")
            self.roi_entry.config(fg="gray")
    
    
    def set_detection_thread(self, detection_thread):
        self.detection_thread = detection_thread
    
    
    def detection_loop(self):
        tab_name = self.tab_name
        while self.detection_thread:
            window_title = self.mainframe.window_title_entry.get()
            game_window_found = False
            similarity_threshold = self.threshold_scale.get()
            
            
            while not game_window_found and not (self.detection_thread is None or self.detection_thread.stopped):
                for window in gw.getWindowsWithTitle(window_title):
                    if window.isActive:
                        game_window_found = True
                        break
                if not game_window_found and not (self.detection_thread is None or self.detection_thread.stopped):
                    self.mainframe.log(f"{tab_name} found no Game window.")
                    time.sleep(5)

            if self.detection_thread is None or self.detection_thread.stopped:
                break  
                
            try:
                x, y, width, height = map(int, self.roi_entry.get().split())
                screenshot_pil = pyautogui.screenshot(region=(x, y, width, height))
                screenshot_np = np.array(screenshot_pil)
                screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
                    
                # Save the main screenshot to the screenshotsfolder
                #timestamp = time.strftime("%Y%m%d%H%M%S")
                #screenshot_filename = os.path.join(self.screenshots_folder, f"screenshot_{timestamp}.png")
                #cv2.imwrite(screenshot_filename, screenshot_cv)
                
                
                best_mse = float("inf")
                best_match_category = None

                for category_name in os.listdir(self.categories_folder):
                    category_folder = os.path.join(self.categories_folder, category_name)
                    if os.path.isdir(category_folder):
                        for image_filename in os.listdir(category_folder):
                            image_path = os.path.join(category_folder, image_filename)
                            template = cv2.imread(image_path)

                            if template is not None and template.shape[:2] == screenshot_cv.shape[:2]:
                                mse = np.mean((screenshot_cv.astype("float") - template.astype("float")) ** 2)

                                #if mse < similarity_threshold:
                                if mse < best_mse:
                                    best_mse = mse
                                    best_match_category = category_name
                                
                
                if best_mse < similarity_threshold and best_match_category:
                    # Valid match found
                    self.mainframe.log(f"{tab_name}: {best_match_category}:{int(best_mse)}")
                    file_path = os.path.join("Trigger", f"Read_with_OBS_{tab_name}.txt")
                    with open(file_path, 'w') as file:
                        file.write(best_match_category)
                else:               
                    file_path = os.path.join("Trigger", f"Read_with_OBS_{tab_name}.txt")
                    with open(file_path, 'w') as file:
                        file.write("None")
                        self.mainframe.log(f"{tab_name}: No quality match:{int(best_mse)}")
                

            except Exception as e:
                self.mainframe.log(f"An error occurred, whilest comparing: {e}")
                
            screenshot_pil = None
            screenshot_np = None
            screenshot_cv = None
            category_name = None
            time.sleep(self.current_speed)

        self.mainframe.log(f"Detection loop {tab_name} exited ")


if __name__ == "__main__":

   
#--------------Lizenz---------------------------------
    # Laden der Konfiguration aus config2.ini
    config2 = configparser.ConfigParser()
    config2.read('config2.ini')

    # Funktion zur Überprüfung, ob die Lizenz bereits akzeptiert wurde
    def is_license_accepted():
        return 'Settings' in config2 and 'LicenseAccepted' in config2['Settings'] and config2['Settings']['LicenseAccepted'] == 'True'

    # Funktion zur Lizenzüberprüfung
    def check_license():
        if not is_license_accepted():
            show_license_agreement()#---------------------------------------------------

   
    # Funktion zur Anzeige der Lizenzvereinbarung
    def show_license_agreement():
        window = tk.Tk()
        window.title("Lizenzvereinbarung")

        # Öffnen der Lizenzvereinbarungsdatei und Lesen des Inhalts
        with open(resource_path('Lizenzvereinbarung.txt'), 'r') as file:
            license_text = file.read()

        text_widget = tk.Text(window)
        text_widget.insert("1.0", license_text)
        text_widget.pack()

        # Funktion zum Akzeptieren der Lizenz
        def accept_license():
            if 'Settings' not in config2:
                config2['Settings'] = {}
            config2['Settings']['LicenseAccepted'] = 'True'
            with open('config2.ini', 'w') as configfile:
                config2.write(configfile)
            window.destroy()
            

        accept_button = tk.Button(window, text="Akzeptieren", command=accept_license)
        accept_button.pack()

        window.mainloop()

    # Überprüfen Sie die Lizenz und starten Sie das Programm
    

   
   
#--------------Keys---------------------------------   
    
    valid_license_keys = [
                "ICTWO5KIRYJCIWFZ", "IKX7H0XEAZERQ69Z", "1JVTHB10UL6TKUTD", "RJR581E0Y6GGAAGX", 
                ]
    
config_file2 = "config2.ini"
config2 = configparser.ConfigParser()

if not os.path.exists(config_file2):
    # If the config file doesn't exist, create it and add the 'License' section
    config2['License'] = {}
    with open(config_file2, "w") as configfile2:
        config2.write(configfile2)
else:
    config2.read(config_file2)


# Check if a license key is present in the config
license_key = config2.get("License", "license_key", fallback='')


if 'License' in config2 and 'license_key' in config2['License']:
    license_key = config2.get("License", "license_key")
    if license_key in valid_license_keys:
        print("Valid license key found. Program started.")
        check_license()
        # Add your program's logic here
else:
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Prompt the user to enter a license key
    while True:
        user_license_key = simpledialog.askstring("License Key", "Enter a valid license key:")

        if user_license_key:
            if user_license_key in valid_license_keys:
                # Update the config file with the entered key
                config2['License']['license_key'] = user_license_key
                with open(config_file2, "w") as configfile2:
                    config2.write(configfile2)
                print("License key saved.")
                check_license()
                # Add your program's logic here
                break
            else:
                print("Invalid license key. Please try again.")

    

            
#--------------Main---------------------------------


root = tk.Tk()
root.title("EYE")
root.iconbitmap(resource_path('Design/Fluffless.ico'))
root.geometry("252x500")

#Gui Images
Img_Play = PhotoImage(file=resource_path("Design/play.png"))
Img_Play = Img_Play.subsample(7, 7)
Img_Stop = PhotoImage(file=resource_path("Design/stop.png"))
Img_Stop = Img_Stop.subsample(7, 7)
Img_New = PhotoImage(file=resource_path("Design/new.png"))
Img_New = Img_New.subsample(7, 7)
Img_Save = PhotoImage(file=resource_path("Design/save.png"))
Img_Save = Img_Save.subsample(7, 7)
Img_Load = PhotoImage(file=resource_path("Design/load.png"))
Img_Load = Img_Load.subsample(7, 7)
Img_Screenshot = PhotoImage(file=resource_path("Design/screenshot.png"))
Img_Screenshot = Img_Screenshot.subsample(7, 7)
Img_Setgame = PhotoImage(file=resource_path("Design/setgame.png"))
Img_Setgame = Img_Setgame.subsample(7, 7)
Img_Fluffy = PhotoImage(file=resource_path("Design/flufflessmclink.png"))
Img_Fluffy = Img_Fluffy.subsample(7, 7)

# Allow the height to be adjustable
root.resizable(width=True, height=True)

root.configure(bg='#403e3e')

style = ttk.Style()
style.theme_create("my_style", parent="alt", settings={
    "TNotebook": {
        "configure": {"background": "#403e3e"},
    },
    "TNotebook.Tab": {
        "configure": {"background": "#403e3e"},
        "map": {"background": [("selected", "#403e3e")],
    }}})
style.theme_use("my_style")

style.map("TNotebook.Tab", foreground=[("selected", "white")])

notebook = ttk.Notebook(root)
frame1 = tk.Frame(notebook, background="#403e3e")  # Set the background color of the frame
frame2 = tk.Frame(notebook, background="#403e3e")  # Set the background color of the frame

tab_names = [str(i) for i in range(1, 11)]

tab1_content = MainFrame(root, config_file, tab_names)

   
    
root.mainloop()