import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import threading
import time
import math
import json
import xml.etree.ElementTree as ET
import subprocess
import tkintermapview  # For embedded map
import random  # For random walk
import pyperclip  # For clipboard pasting; pip install pyperclip

ctk.set_appearance_mode("System")  # Use system appearance for true macOS feel
ctk.set_default_color_theme("blue")

class PolypathApp:
    def __init__(self, root):
        self.root = root
        self.root.title("iOS GPS Spoofer made by Chucny")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        self.device_connected = False
        self.current_lat = 37.7749
        self.current_lon = -122.4194
        self.current_alt = 0.0  # Note: Altitude not directly supported in iOS simulation
        self.accuracy = 5.0
        self.bearing = 0.0
        self.speed = 1.4  # m/s walking, good for Pokémon Go
        self.path = []
        self.favorites = {}
        self.is_simulating = False
        self.is_paused = False
        self.joystick_radius = 100
        self.handle_pos = [0, 0]
        self.load_favorites()
        self.setup_ui()
        self.connect_device()

    def setup_ui(self):
        # Main container
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure((0,1), weight=1)
        
        # Sidebar
        sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        ctk.CTkLabel(sidebar, text="iOS GPS Spoofer", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        ctk.CTkLabel(sidebar, text="Always free!", font=ctk.CTkFont(size=12, slant="italic")).pack(pady=5)
        
        # Location controls
        ctk.CTkLabel(sidebar, text="Coordinates", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10,0))
        self.lat_entry = ctk.CTkEntry(sidebar, placeholder_text="Latitude")
        self.lat_entry.pack(padx=20, pady=5, fill="x")
        self.lat_entry.insert(0, str(self.current_lat))
        self.lon_entry = ctk.CTkEntry(sidebar, placeholder_text="Longitude")
        self.lon_entry.pack(padx=20, pady=5, fill="x")
        self.lon_entry.insert(0, str(self.current_lon))
        self.alt_entry = ctk.CTkEntry(sidebar, placeholder_text="Altitude (m) - Not supported")
        self.alt_entry.pack(padx=20, pady=5, fill="x")
        self.alt_entry.insert(0, str(self.current_alt))
        self.alt_entry.configure(state="disabled")  # Disable since not supported
        
        coord_btn_frame = ctk.CTkFrame(sidebar)
        coord_btn_frame.pack(padx=20, pady=10, fill="x")
        ctk.CTkButton(coord_btn_frame, text="Set Location", command=self.set_location).pack(side="left", expand=True, fill="x")
        ctk.CTkButton(coord_btn_frame, text="Paste Coords", command=self.paste_coords).pack(side="left", padx=5, expand=True, fill="x")
        
        # Pokémon Go Tips
        ctk.CTkLabel(sidebar, text="Pokémon Go Mode", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20,0))
        ctk.CTkButton(sidebar, text="Start Egg Hatching Circle", command=self.start_egg_hatch).pack(padx=20, pady=5, fill="x")
        ctk.CTkButton(sidebar, text="Random Walk (Anti-Ban)", command=self.start_random_walk).pack(padx=20, pady=5, fill="x")
        self.cooldown_switch = ctk.CTkSwitch(sidebar, text="Enable Cooldown (2h after jump >500km)")
        self.cooldown_switch.pack(padx=20, pady=5)
        
        # Favorites
        ctk.CTkLabel(sidebar, text="Favorites", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20,0))
        self.fav_entry = ctk.CTkEntry(sidebar, placeholder_text="Name")
        self.fav_entry.pack(padx=20, pady=5, fill="x")
        ctk.CTkButton(sidebar, text="Add Favorite", command=self.add_favorite).pack(padx=20, pady=5, fill="x")
        self.fav_list = ctk.CTkScrollableFrame(sidebar, height=120)
        self.fav_list.pack(padx=20, pady=5, fill="x")
        self.update_fav_list()
        
        # Main area
        main = ctk.CTkFrame(self.root)
        main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure((0,2), weight=1)
        
        # Status
        self.status = ctk.CTkLabel(main, text="Status: Disconnected", font=ctk.CTkFont(size=14))
        self.status.pack(pady=10)
        
        # Map View
        map_frame = ctk.CTkFrame(main)
        map_frame.pack(fill="both", expand=True, pady=10)
        self.map_widget = tkintermapview.TkinterMapView(map_frame, width=800, height=400, corner_radius=10)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(self.current_lat, self.current_lon)
        self.map_widget.set_zoom(15)
        self.map_marker = self.map_widget.set_marker(self.current_lat, self.current_lon, text="Current Location")
        self.map_widget.add_right_click_menu_command(label="Set Location Here", command=self.set_from_map)
        
        # Joystick
        joy_frame = ctk.CTkFrame(main)
        joy_frame.pack(pady=20)
        self.canvas = tk.Canvas(joy_frame, width=260, height=260, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack()
        self.draw_joystick()
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Controls
        ctrl = ctk.CTkFrame(main)
        ctrl.pack(pady=10, fill="x")
        ctk.CTkLabel(ctrl, text="Speed (m/s):").grid(row=0, column=0, padx=10)
        self.speed_slider = ctk.CTkSlider(ctrl, from_=0.5, to=30, command=self.update_speed)
        self.speed_slider.set(self.speed)
        self.speed_slider.grid(row=0, column=1, padx=10)
        
        # Path & Simulation
        path_frame = ctk.CTkFrame(main)
        path_frame.pack(pady=10, fill="x")
        ctk.CTkButton(path_frame, text="Add to Path", command=self.add_to_path).pack(side="left", padx=10)
        ctk.CTkButton(path_frame, text="Clear Path", command=self.clear_path).pack(side="left", padx=10)
        ctk.CTkButton(path_frame, text="Start Simulation", command=self.start_simulation).pack(side="left", padx=10)
        ctk.CTkButton(path_frame, text="Pause/Resume", command=self.toggle_pause).pack(side="left", padx=10)
        ctk.CTkButton(path_frame, text="Stop", command=self.stop_simulation).pack(side="left", padx=10)
        ctk.CTkButton(path_frame, text="Orbit Mode", command=self.start_orbit).pack(side="left", padx=10)
        
        # Path list
        self.path_list = ctk.CTkScrollableFrame(main, height=100)
        self.path_list.pack(fill="x", padx=20, pady=10)
        
        # Export/Import
        btn_frame = ctk.CTkFrame(main)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Export Path (GPX)", command=self.export_gpx).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Import GPX", command=self.import_gpx).pack(side="left", padx=10)

    def draw_joystick(self):
        self.canvas.delete("all")
        # Outer ring
        self.canvas.create_oval(30, 30, 230, 230, outline="#3498db", width=4)
        # Center
        cx, cy = 130, 130
        self.handle = self.canvas.create_oval(cx-20, cy-20, cx+20, cy+20, fill="#3498db", outline="white")

    def on_drag(self, event):
        cx, cy = 130, 130
        dx = event.x - cx
        dy = event.y - cy
        dist = min(math.hypot(dx, dy), self.joystick_radius)
        if dist > 0:
            angle = math.atan2(dy, dx)
            dx = dist * math.cos(angle)
            dy = dist * math.sin(angle)
        self.canvas.coords(self.handle, cx + dx - 20, cy + dy - 20, cx + dx + 20, cy + dy + 20)
        self.handle_pos = [dx / self.joystick_radius, dy / self.joystick_radius]
        dlat = self.handle_pos[1] * -0.00001  # Invert for natural movement (up = north)
        dlon = self.handle_pos[0] * 0.00001
        self.move(dlat, dlon)

    def on_release(self, event):
        self.draw_joystick()
        self.handle_pos = [0, 0]

    def set_from_map(self, coord):
        self.current_lat, self.current_lon = coord
        self.update_entries()
        self.send_location()
        self.map_marker.set_position(coord)

    def connect_device(self):
        try:
            # Check if device is connected by listing devices
            result = subprocess.check_output(['pymobiledevice3', 'devices', 'list']).decode('utf-8')
            if 'No devices found' in result:
                raise Exception("No iOS device connected")
            self.device_connected = True
            self.status.configure(text="Status: Connected ✓", text_color="green")
        except Exception as e:
            self.status.configure(text=f"Status: {str(e)} - Ensure Developer Mode is enabled", text_color="red")

    def send_location(self):
        if not self.device_connected:
            return
        try:
            subprocess.check_call([
                'pymobiledevice3',
                'developer',
                'dvt',
                'simulate-location',
                'set',
                str(self.current_lat),
                str(self.current_lon)
            ])
            time.sleep(0.1)  # Small delay for smooth spoofing
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set location: {e}")

    def set_location(self):
        try:
            if self.cooldown_switch.get() and self.check_cooldown_needed():
                messagebox.showwarning("Cooldown", "Cooldown active! Wait 2 hours for jumps >500km.")
                return
            self.current_lat = float(self.lat_entry.get())
            self.current_lon = float(self.lon_entry.get())
            self.current_alt = float(self.alt_entry.get() or 0)
            self.send_location()
            self.map_widget.set_position(self.current_lat, self.current_lon)
            self.map_marker.set_position((self.current_lat, self.current_lon))
            messagebox.showinfo("Success", "Location spoofed!")
        except ValueError:
            messagebox.showerror("Error", "Invalid input")

    def quick_set(self, lat, lon):
        self.current_lat, self.current_lon = lat, lon
        self.lat_entry.delete(0, tk.END)
        self.lat_entry.insert(0, str(lat))
        self.lon_entry.delete(0, tk.END)
        self.lon_entry.insert(0, str(lon))
        self.send_location()
        self.map_widget.set_position(lat, lon)
        self.map_marker.set_position((lat, lon))

    def move(self, dlat, dlon):
        self.current_lat += dlat
        self.current_lon += dlon
        self.lat_entry.delete(0, tk.END)
        self.lat_entry.insert(0, f"{self.current_lat:.6f}")
        self.lon_entry.delete(0, tk.END)
        self.lon_entry.insert(0, f"{self.current_lon:.6f}")
        self.send_location()
        self.map_widget.set_position(self.current_lat, self.current_lon)
        self.map_marker.set_position((self.current_lat, self.current_lon))

    def add_to_path(self):
        self.path.append((self.current_lat, self.current_lon, self.current_alt))
        lbl = ctk.CTkLabel(self.path_list, text=f"→ {self.current_lat:.6f}, {self.current_lon:.6f}")
        lbl.pack(anchor="w", padx=10)
        self.map_widget.set_marker(self.current_lat, self.current_lon, text=f"Path Point {len(self.path)}")

    def clear_path(self):
        self.path = []
        for w in self.path_list.winfo_children():
            w.destroy()

    def start_simulation(self):
        if not self.path or self.is_simulating:
            return
        self.is_simulating = True
        self.is_paused = False
        threading.Thread(target=self.simulate, daemon=True).start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused

    def stop_simulation(self):
        self.is_simulating = False

    def simulate(self):
        while self.is_simulating and len(self.path) > 1:
            if self.is_paused:
                time.sleep(0.1)
                continue
            for i in range(len(self.path) - 1):
                if not self.is_simulating:
                    break
                start = self.path[i]
                end = self.path[i + 1]
                dist = self.haversine(start[:2], end[:2]) * 1000
                steps = max(1, int(dist / self.speed))
                dlat = (end[0] - start[0]) / steps
                dlon = (end[1] - start[1]) / steps
                dalt = (end[2] - start[2]) / steps
                for _ in range(steps):
                    if not self.is_simulating or self.is_paused:
                        break
                    self.current_lat += dlat
                    self.current_lon += dlon
                    self.current_alt += dalt
                    self.send_location()
                    self.root.after(0, self.update_entries)
                    self.root.after(0, lambda lat=self.current_lat, lon=self.current_lon: self.map_widget.set_position(lat, lon))
                    self.root.after(0, lambda lat=self.current_lat, lon=self.current_lon: self.map_marker.set_position(lat, lon))
                    time.sleep(1)
        self.is_simulating = False

    def update_entries(self):
        self.lat_entry.delete(0, tk.END)
        self.lat_entry.insert(0, f"{self.current_lat:.6f}")
        self.lon_entry.delete(0, tk.END)
        self.lon_entry.insert(0, f"{self.current_lon:.6f}")
        self.alt_entry.delete(0, tk.END)
        self.alt_entry.insert(0, f"{self.current_alt:.1f}")

    def update_speed(self, val):
        self.speed = float(val)

    def start_orbit(self):
        if self.is_simulating:
            return
        self.is_simulating = True
        threading.Thread(target=self.orbit, daemon=True).start()

    def orbit(self):
        radius = 0.0003  # Smaller radius for Pokémon Go gyms/parks ~30m
        steps = 360
        for i in range(steps * 10):  # Longer loops for hatching
            if not self.is_simulating:
                break
            angle = math.radians(i)
            self.current_lat = self.current_lat + radius * math.cos(angle)
            self.current_lon = self.current_lon + radius * math.sin(angle) / math.cos(math.radians(self.current_lat))
            self.send_location()
            self.root.after(0, self.update_entries)
            self.root.after(0, lambda lat=self.current_lat, lon=self.current_lon: self.map_widget.set_position(lat, lon))
            self.root.after(0, lambda lat=self.current_lat, lon=self.current_lon: self.map_marker.set_position(lat, lon))
            time.sleep(0.5)  # Slower for realism
        self.is_simulating = False

    def start_egg_hatch(self):
        self.speed = 1.0  # Slow walking for eggs
        self.start_orbit()  # Use orbit for circular walking

    def start_random_walk(self):
        if self.is_simulating:
            return
        self.is_simulating = True
        threading.Thread(target=self.random_walk, daemon=True).start()

    def random_walk(self):
        while self.is_simulating:
            if self.is_paused:
                time.sleep(0.1)
                continue
            dlat = (random.uniform(-1, 1) * 0.00005)  # ~5m random
            dlon = (random.uniform(-1, 1) * 0.00005)
            self.move(dlat, dlon)
            time.sleep(random.uniform(1, 3))  # Random pauses
        self.is_simulating = False

    def check_cooldown_needed(self):
        # Simple distance check; store last pos in file or var
        try:
            with open("last_pos.json", "r") as f:
                last = json.load(f)
            dist = self.haversine((last["lat"], last["lon"]), (self.current_lat, self.current_lon))
            if dist > 500:
                return True
        except:
            pass
        with open("last_pos.json", "w") as f:
            json.dump({"lat": self.current_lat, "lon": self.current_lon}, f)
        return False

    def haversine(self, c1, c2):
        R = 6371
        dlat = math.radians(c2[0] - c1[0])
        dlon = math.radians(c2[1] - c1[1])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(c1[0])) * math.cos(math.radians(c2[0])) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def add_favorite(self):
        name = self.fav_entry.get()
        if name:
            self.favorites[name] = (self.current_lat, self.current_lon, self.current_alt)
            self.update_fav_list()
            self.fav_entry.delete(0, tk.END)

    def update_fav_list(self):
        for w in self.fav_list.winfo_children():
            w.destroy()
        for name, (lat, lon, alt) in self.favorites.items():
            btn = ctk.CTkButton(self.fav_list, text=f"{name} ({lat:.4f}, {lon:.4f})",
                                command=lambda l=lat, o=lon: self.quick_set(l, o))
            btn.pack(fill="x", pady=2)

    def load_favorites(self):
        try:
            with open("favorites.json") as f:
                self.favorites = json.load(f)
        except:
            pass

    def save_favorites(self):
        with open("favorites.json", "w") as f:
            json.dump(self.favorites, f)

    def export_gpx(self):
        if not self.path:
            return
        file = filedialog.asksaveasfilename(defaultextension=".gpx")
        if file:
            root = ET.Element("gpx", version="1.1", creator="iOS GPS Spoofer (based on Chucny's PolypathInjector)")
            trk = ET.SubElement(root, "trk")
            seg = ET.SubElement(trk, "trkseg")
            for lat, lon, alt in self.path:
                wpt = ET.SubElement(seg, "trkpt", lat=str(lat), lon=str(lon))
                ET.SubElement(wpt, "ele").text = str(alt)
            tree = ET.ElementTree(root)
            tree.write(file, encoding="utf-8", xml_declaration=True)

    def import_gpx(self):
        file = filedialog.askopenfilename(filetypes=[("GPX", "*.gpx")])
        if file:
            tree = ET.parse(file)
            self.path = []
            for trkpt in tree.findall(".//{*}trkpt"):
                lat = float(trkpt.get("lat"))
                lon = float(trkpt.get("lon"))
                alt = float(trkpt.find("{*}ele").text or 0) if trkpt.find("{*}ele") is not None else 0
                self.path.append((lat, lon, alt))
            self.clear_path()
            for p in self.path:
                lbl = ctk.CTkLabel(self.path_list, text=f"→ {p[0]:.6f}, {p[1]:.6f}")
                lbl.pack(anchor="w", padx=10)

    def paste_coords(self):
        try:
            clipboard = pyperclip.paste().strip()
            if ',' in clipboard:
                lat, lon = map(float, clipboard.split(','))
                self.lat_entry.delete(0, tk.END)
                self.lat_entry.insert(0, str(lat))
                self.lon_entry.delete(0, tk.END)
                self.lon_entry.insert(0, str(lon))
                messagebox.showinfo("Success", "Coordinates pasted from clipboard!")
            else:
                messagebox.showerror("Error", "Invalid format in clipboard. Expect 'lat,lon'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to paste: {e}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = PolypathApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.save_favorites(), root.destroy()))
    root.mainloop()